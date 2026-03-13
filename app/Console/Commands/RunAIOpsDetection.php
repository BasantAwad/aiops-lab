<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Services\PrometheusClient;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class RunAIOpsDetection extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'aiops:detect';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Run the AIOps Detection Engine continuously.';

    protected $endpoints = [
        '/api/normal',
        '/api/slow',
        '/api/db',
        '/api/error',
        '/api/validate'
    ];

    protected $activeAlerts = [];

    /**
     * Execute the console command.
     */
    public function handle(PrometheusClient $prometheus)
    {
        $this->info("Starting AIOps Detection Engine...");

        // Ensure incidents storage directory exists
        $incidentsDir = storage_path('aiops');
        if (!is_dir($incidentsDir)) {
            mkdir($incidentsDir, 0755, true);
        }

        while (true) {
            $this->info("--- Scanning cycle --- " . now()->toDateTimeString());

            $detectedAnomalies = [];

            foreach ($this->endpoints as $endpoint) {
                // Determine baselines and current metrics

                // 1. Latency (95th percentile)
                $baselineLatency = $prometheus->queryScalar("histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{path=\"{$endpoint}\"}[1h])) by (le))");
                $currentLatency = $prometheus->queryScalar("histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{path=\"{$endpoint}\"}[1m])) by (le))");

                // 2. Request Rate
                $baselineRate = $prometheus->queryScalar("sum(rate(http_requests_total{path=\"{$endpoint}\"}[1h]))");
                $currentRate = $prometheus->queryScalar("sum(rate(http_requests_total{path=\"{$endpoint}\"}[1m]))");

                // 3. Error Rate (Status >= 400)
                // Total requests (1h vs 1m)
                $baselineTotalReqs = $baselineRate; // since it's already a rate
                $baselineErrors = $prometheus->queryScalar("sum(rate(http_requests_total{path=\"{$endpoint}\", status=~\"4..|5..\"}[1h]))");
                $currentErrors = $prometheus->queryScalar("sum(rate(http_requests_total{path=\"{$endpoint}\", status=~\"4..|5..\"}[1m]))");

                $baselineErrorRate = $baselineTotalReqs > 0 ? ($baselineErrors / $baselineTotalReqs) : 0;
                $currentErrorRate = $currentRate > 0 ? ($currentErrors / $currentRate) : 0;

                $this->line("Endpoint: {$endpoint} | Latency: " . round($currentLatency, 4) . "s (Base: " . round($baselineLatency, 4) . "s) | Rate: " . round($currentRate, 2) . "/s (Base: " . round($baselineRate, 2) . "/s) | Err Rate: " . round($currentErrorRate * 100, 2) . "% (Base: " . round($baselineErrorRate * 100, 2) . "%)");

                // Anomaly Detection Rules
                $endpointAnomalies = [];

                // Latency > 3 x baseline (and baseline has some sensible min value > 0)
                if ($baselineLatency > 0.01 && $currentLatency > (3 * $baselineLatency)) {
                    $endpointAnomalies[] = 'LATENCY_SPIKE';
                }

                // Error Rate > 10%
                if ($currentErrorRate > 0.10) {
                    $endpointAnomalies[] = 'ERROR_STORM';
                }

                // Traffic Spike > 2 x baseline
                if ($baselineRate > 1 && $currentRate > (2 * $baselineRate)) {
                    $endpointAnomalies[] = 'TRAFFIC_SURGE';
                }

                if (!empty($endpointAnomalies)) {
                    $detectedAnomalies[$endpoint] = [
                        'anomalies' => $endpointAnomalies,
                        'current' => ['latency' => $currentLatency, 'rate' => $currentRate, 'error_rate' => $currentErrorRate],
                        'baseline' => ['latency' => $baselineLatency, 'rate' => $baselineRate, 'error_rate' => $baselineErrorRate],
                    ];
                }
            }

            // Event Correlation & Incident Generation
            if (!empty($detectedAnomalies)) {
                $this->correlateAndGenerateIncidents($detectedAnomalies);
            } else {
                $this->activeAlerts = []; // clear active alerts if everything is normal to allow firing again later
            }

            sleep(20);
        }
    }

    protected function correlateAndGenerateIncidents(array $detectedAnomalies)
    {
        $incidentType = '';
        $severity = 'warning';
        $summary = '';

        // Correlate: Are multiple endpoints failing with errors or latency?
        $errorEndpoints = [];
        $latencyEndpoints = [];
        $trafficEndpoints = [];

        foreach ($detectedAnomalies as $endpoint => $data) {
            if (in_array('ERROR_STORM', $data['anomalies']))
                $errorEndpoints[] = $endpoint;
            if (in_array('LATENCY_SPIKE', $data['anomalies']))
                $latencyEndpoints[] = $endpoint;
            if (in_array('TRAFFIC_SURGE', $data['anomalies']))
                $trafficEndpoints[] = $endpoint;
        }

        if (count($errorEndpoints) > 1 || count($latencyEndpoints) > 1) {
            $incidentType = 'SERVICE_DEGRADATION';
            $severity = 'critical';
            $summary = "Multiple endpoints degraded. Errors: " . implode(',', $errorEndpoints) . ". Latency issues: " . implode(',', $latencyEndpoints);
        } elseif (!empty($errorEndpoints)) {
            $incidentType = 'ERROR_STORM';
            $severity = 'error';
            $summary = "High error rate on " . implode(',', $errorEndpoints);
        } elseif (!empty($latencyEndpoints)) {
            $incidentType = 'LATENCY_SPIKE';
            $severity = 'warning';
            $summary = "High latency detected on " . implode(',', $latencyEndpoints);
        } elseif (!empty($trafficEndpoints)) {
            $incidentType = 'TRAFFIC_SURGE';
            $severity = 'info';
            $summary = "Unusual traffic spike on " . implode(',', $trafficEndpoints);
        } else {
            $incidentType = 'LOCALIZED_ENDPOINT_FAILURE';
            $severity = 'warning';
            $summary = "Anomalies detected on specific endpoints.";
        }

        // Deduplication
        // Alert caching logic: hash the type and endpoints
        $alertHash = md5($incidentType . implode(',', array_keys($detectedAnomalies)));

        if (!isset($this->activeAlerts[$alertHash])) {
            // New incident!
            $incident = [
                'incident_id' => (string) Str::uuid(),
                'incident_type' => $incidentType,
                'severity' => $severity,
                'status' => 'OPEN',
                'detected_at' => now()->toIso8601String(),
                'affected_service' => 'Laravel App',
                'affected_endpoints' => array_keys($detectedAnomalies),
                'triggering_signals' => $detectedAnomalies,
                'summary' => $summary,
            ];

            // Alert via console
            $this->error("🚨 ALERT FIRED: [{$incident['severity']}] {$incident['incident_type']} - {$incident['summary']}");

            // Write to incidents.json
            $existing = [];
            $incidentsFile = storage_path('aiops/incidents.json');
            if (file_exists($incidentsFile)) {
                $existing = json_decode(file_get_contents($incidentsFile), true) ?: [];
            }
            $existing[] = $incident;
            file_put_contents($incidentsFile, json_encode($existing, JSON_PRETTY_PRINT));

            $this->activeAlerts[$alertHash] = true;
        } else {
            $this->line("⏳ Ongoing incident ({$incidentType}) suppressed to avoid duplicate alerts.");
        }
    }
}
