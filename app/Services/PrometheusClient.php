<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class PrometheusClient
{
    protected string $baseUrl;

    public function __construct()
    {
        $this->baseUrl = config('services.prometheus.url', 'http://localhost:9090');
    }

    /**
     * Executes a PromQL query against the Prometheus API.
     *
     * @param string $query
     * @return array|null
     */
    public function query(string $query): ?array
    {
        try {
            $response = Http::get("{$this->baseUrl}/api/v1/query", [
                'query' => $query,
            ]);

            if ($response->successful()) {
                $data = $response->json();
                if (isset($data['status']) && $data['status'] === 'success') {
                    return $data['data']['result'] ?? [];
                }
            }

            Log::error('Prometheus query failed format', ['response' => $response->body()]);
            return null;

        } catch (\Exception $e) {
            Log::error('Prometheus query exception', ['exception' => $e->getMessage()]);
            return null;
        }
    }

    /**
     * Helper to get a single scalar value from a query result.
     *
     * @param string $query
     * @return float
     */
    public function queryScalar(string $query): float
    {
        $result = $this->query($query);
        if ($result && count($result) > 0) {
            // result[0]['value'] is typically [timestamp, "valueString"]
            return (float) ($result[0]['value'][1] ?? 0);
        }
        return 0.0;
    }
}
