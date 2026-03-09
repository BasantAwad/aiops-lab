<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use App\Exceptions\Handler;

class TelemetryMiddleware
{
    public function handle(Request $request, Closure $next)
    {
        // Exclude /metrics from logging itself
        if ($request->is('metrics')) {
            return $next($request);
        }

        $startTime = microtime(true);
        $correlationId = $request->header('X-Request-Id', Str::uuid()->toString());

        // Execute the request (no clone — clone loses exception info)
        $response = $next($request);

        $latencySec = microtime(true) - $startTime;
        $latencyMs = round($latencySec * 1000);

        $statusCode = $response->getStatusCode();

        // Determine error category using centralized Handler mapping + timeout override
        $errorCategory = $this->determineErrorCategory($request, $response, $latencyMs);

        // Attach Correlation ID to response header
        $response->headers->set('X-Request-Id', $correlationId);

        // 1. Structured Logging — stable schema (same keys always exist)
        $logData = [
            'timestamp' => now()->toIso8601String(),
            'trace_id' => $correlationId,
            'method' => $request->method(),
            'path' => '/' . $request->path(),
            'client_ip' => $request->ip() ?? 'unknown',
            'user_agent' => $request->userAgent() ?? 'unknown',
            'query' => $request->getQueryString() ?? null,
            'payload_size_bytes' => strlen($request->getContent()) ?: 0,
            'response_size_bytes' => strlen($response->getContent()) ?: 0,
            'route_name' => $request->route() ? $request->route()->getName() : 'unknown',
            'severity' => $statusCode >= 400 || $errorCategory === 'TIMEOUT_ERROR' ? 'error' : 'info',
            'build_version' => env('BUILD_VERSION', '1.0.0'),
            'host' => gethostname(),
            'status_code' => $statusCode,
            'error_category' => $errorCategory,
            'latency_ms' => $latencyMs,
        ];

        // Write directly to custom log file
        file_put_contents(
            storage_path('logs/aiops.log'),
            json_encode($logData) . PHP_EOL,
            FILE_APPEND
        );

        // 2. Metrics Recording
        $this->recordMetrics($request, $statusCode, $errorCategory, $latencySec);

        return $response;
    }

    private function determineErrorCategory($request, $response, $latencyMs)
    {
        // Hard constraint: 200 OK but latency > 4000ms MUST be TIMEOUT_ERROR
        if ($latencyMs > 4000) {
            return 'TIMEOUT_ERROR';
        }

        if ($response->getStatusCode() < 400) {
            return 'NONE';
        }

        // Use centralized Handler categorization if exception exists
        if ($response->exception) {
            return Handler::categorizeError($response->exception);
        }

        return 'UNKNOWN';
    }

    private function recordMetrics($request, $statusCode, $errorCategory, $latencySec)
    {
        $metricsFile = storage_path('framework/prom_metrics/metrics.json');

        // Ensure directory exists
        $dir = dirname($metricsFile);
        if (!is_dir($dir)) {
            mkdir($dir, 0777, true);
        }

        $lock = fopen($metricsFile . '.lock', 'c');
        flock($lock, LOCK_EX);

        $data = file_exists($metricsFile) ? json_decode(file_get_contents($metricsFile), true) : [
            'requests' => [],
            'errors' => [],
            'histograms' => []
        ];

        $method = $request->method();
        $path = $request->path();

        // Counter: http_requests_total
        $reqKey = "{$method}|{$path}|{$statusCode}";
        $data['requests'][$reqKey] = ($data['requests'][$reqKey] ?? 0) + 1;

        // Counter: http_errors_total
        if ($errorCategory !== 'NONE') {
            $errKey = "{$method}|{$path}|{$errorCategory}";
            $data['errors'][$errKey] = ($data['errors'][$errKey] ?? 0) + 1;
        }

        // Histogram: store observation in ONLY the smallest matching bucket
        // The /metrics renderer will then produce cumulative counts
        $buckets = [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10];
        $histKey = "{$method}|{$path}";
        if (!isset($data['histograms'][$histKey])) {
            $data['histograms'][$histKey] = [
                'sum' => 0,
                'count' => 0,
                'buckets' => array_fill_keys(array_map('strval', $buckets), 0)
            ];
        }

        $data['histograms'][$histKey]['sum'] += $latencySec;
        $data['histograms'][$histKey]['count'] += 1;

        // Put observation into the smallest bucket that fits
        $placed = false;
        foreach ($buckets as $bucket) {
            if ($latencySec <= $bucket && !$placed) {
                $data['histograms'][$histKey]['buckets'][(string) $bucket]++;
                $placed = true;
                break;
            }
        }
        // If latencySec > 10 (largest bucket), it only goes in +Inf (handled by count)

        file_put_contents($metricsFile, json_encode($data));
        flock($lock, LOCK_UN);
        fclose($lock);
    }
}