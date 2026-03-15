<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ApiController extends Controller
{
    /**
     * [LAB 1] Endpoint: /api/normal
     * Simulates normal application behavior with a quick response.
     */
    public function normal()
    {
        return response()->json(['status' => 'success', 'data' => 'Normal behavior']);
    }

    /**
     * [LAB 1] Endpoint: /api/slow
     * Simulates a delayed response depending on the 'hard' query parameter.
     */
    public function slow(Request $request)
    {
        if ($request->query('hard') == 1) {
            sleep(rand(5, 7)); // Hard slow — will trigger TIMEOUT_ERROR
        } else {
            usleep(rand(500000, 1500000)); // Normal slow (0.5 - 1.5s)
        }
        return response()->json(['status' => 'success', 'data' => 'Delayed behavior']);
    }

    /**
     * [LAB 1] Endpoint: /api/error
     * Simulates an unexpected server error by throwing a generic exception.
     */
    public function error()
    {
        throw new \Exception("Simulated System Error");
    }

    /**
     * [LAB 1] Endpoint: /api/random
     * Simulates random errors (20% chance of throwing an exception).
     */
    public function random()
    {
        if (rand(1, 10) > 8)
            throw new \Exception("Random System Error");
        return response()->json(['status' => 'success', 'data' => 'Random behavior']);
    }

    /**
     * [LAB 1] Endpoint: /api/db
     * Simulates database interaction, capable of triggering a QueryException.
     */
    public function db(Request $request)
    {
        if ($request->query('fail') == 1) {
            // Force a QueryException
            DB::table('non_existent_table_123')->get();
        }

        $data = DB::table('dummy_data')->get();
        return response()->json(['status' => 'success', 'data' => $data]);
    }

    /**
     * [LAB 1] Endpoint: /api/validate
     * Simulates user input validation, expecting payload parameters.
     */
    public function validateData(Request $request)
    {
        $request->validate([
            'email' => 'required|email',
            'age' => 'required|integer|between:18,60',
        ]);

        return response()->json(['status' => 'success', 'data' => 'Valid input']);
    }

    /**
     * [LAB 1] Endpoint: /metrics
     * Exposes metrics in Prometheus text-based exporter format by parsing 
     * the local metrics.json file populated by TelemetryMiddleware.
     */
    public function metrics()
    {
        $metricsFile = storage_path('framework/prom_metrics/metrics.json');
        if (!file_exists($metricsFile))
            return response('', 200)->header('Content-Type', 'text/plain');

        $data = json_decode(file_get_contents($metricsFile), true);
        $output = "";

        // Requests Counter
        $output .= "# HELP http_requests_total Total number of HTTP requests.\n";
        $output .= "# TYPE http_requests_total counter\n";
        foreach (($data['requests'] ?? []) as $key => $val) {
            [$method, $path, $status] = explode('|', $key);
            $output .= "http_requests_total{method=\"$method\",path=\"/$path\",status=\"$status\"} $val\n";
        }

        // Errors Counter
        $output .= "# HELP http_errors_total Total number of HTTP errors.\n";
        $output .= "# TYPE http_errors_total counter\n";
        foreach (($data['errors'] ?? []) as $key => $val) {
            [$method, $path, $category] = explode('|', $key);
            $output .= "http_errors_total{method=\"$method\",path=\"/$path\",error_category=\"$category\"} $val\n";
        }

        // Histogram — render with cumulative bucket counts
        $output .= "# HELP http_request_duration_seconds HTTP request duration in seconds.\n";
        $output .= "# TYPE http_request_duration_seconds histogram\n";
        foreach (($data['histograms'] ?? []) as $key => $stats) {
            [$method, $path] = explode('|', $key);
            $cumulative = 0;
            foreach ($stats['buckets'] as $le => $count) {
                $cumulative += $count;
                $output .= "http_request_duration_seconds_bucket{method=\"$method\",path=\"/$path\",le=\"$le\"} $cumulative\n";
            }
            // +Inf bucket = total count (all observations)
            $output .= "http_request_duration_seconds_bucket{method=\"$method\",path=\"/$path\",le=\"+Inf\"} {$stats['count']}\n";
            $output .= "http_request_duration_seconds_sum{method=\"$method\",path=\"/$path\"} {$stats['sum']}\n";
            $output .= "http_request_duration_seconds_count{method=\"$method\",path=\"/$path\"} {$stats['count']}\n";
        }

        return response($output, 200)->header('Content-Type', 'text/plain');
    }
}