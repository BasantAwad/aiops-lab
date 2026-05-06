<?php

/**
 * ============================================================================
 * [LAB WORK 5] - AIOps Response Policy Configuration
 * Defines the automated response policies for each incident type detected by
 * the Lab 2 detection engine. Each policy specifies the actions to execute,
 * escalation thresholds, and cooldown periods.
 * ============================================================================
 */

return [

    /*
    |--------------------------------------------------------------------------
    | Response Policies
    |--------------------------------------------------------------------------
    | Maps incident_type => response configuration.
    | Each policy defines:
    |   - actions:    Ordered list of automated actions to execute
    |   - escalation: What happens if the action fails or anomaly persists
    |   - cooldown:   Seconds before the same incident can be re-responded to
    |   - max_retries: How many times to retry before escalating
    */

    'policies' => [

        'LATENCY_SPIKE' => [
            'actions' => [
                [
                    'type'        => 'restart_service',
                    'target'      => 'php-fpm',
                    'description' => 'Restart PHP-FPM worker pool to clear stuck processes',
                    'timeout'     => 30,
                ],
                [
                    'type'        => 'flush_cache',
                    'target'      => 'application',
                    'description' => 'Clear application and route caches to eliminate stale entries',
                    'timeout'     => 10,
                ],
            ],
            'escalation' => 'CRITICAL_ALERT',
            'cooldown'   => 120,
            'max_retries' => 2,
        ],

        'ERROR_STORM' => [
            'actions' => [
                [
                    'type'        => 'send_alert',
                    'target'      => 'ops-team',
                    'description' => 'Send high-priority alert to on-call operations team',
                    'timeout'     => 5,
                ],
                [
                    'type'        => 'throttle_traffic',
                    'target'      => 'affected_endpoints',
                    'description' => 'Enable rate limiting on affected endpoints to reduce error volume',
                    'timeout'     => 10,
                ],
            ],
            'escalation' => 'CRITICAL_ALERT',
            'cooldown'   => 60,
            'max_retries' => 3,
        ],

        'TRAFFIC_SURGE' => [
            'actions' => [
                [
                    'type'        => 'scale_service',
                    'target'      => 'web-workers',
                    'description' => 'Scale horizontal worker count from 2 to 6 instances',
                    'timeout'     => 60,
                ],
                [
                    'type'        => 'enable_queue',
                    'target'      => 'request-queue',
                    'description' => 'Activate request queuing to absorb traffic burst',
                    'timeout'     => 15,
                ],
            ],
            'escalation' => 'CRITICAL_ALERT',
            'cooldown'   => 180,
            'max_retries' => 2,
        ],

        'SERVICE_DEGRADATION' => [
            'actions' => [
                [
                    'type'        => 'send_alert',
                    'target'      => 'ops-team',
                    'description' => 'Page on-call engineer for multi-endpoint service degradation',
                    'timeout'     => 5,
                ],
                [
                    'type'        => 'restart_service',
                    'target'      => 'php-fpm',
                    'description' => 'Restart PHP-FPM to recover degraded workers',
                    'timeout'     => 30,
                ],
                [
                    'type'        => 'throttle_traffic',
                    'target'      => 'affected_endpoints',
                    'description' => 'Apply emergency rate limits across degraded endpoints',
                    'timeout'     => 10,
                ],
            ],
            'escalation' => 'CRITICAL_ALERT',
            'cooldown'   => 60,
            'max_retries' => 2,
        ],

        'LOCALIZED_ENDPOINT_FAILURE' => [
            'actions' => [
                [
                    'type'        => 'send_alert',
                    'target'      => 'dev-team',
                    'description' => 'Notify development team of localized endpoint failure',
                    'timeout'     => 5,
                ],
                [
                    'type'        => 'enable_circuit_breaker',
                    'target'      => 'affected_endpoints',
                    'description' => 'Trip circuit breaker to return fast-fail responses',
                    'timeout'     => 5,
                ],
            ],
            'escalation' => 'CRITICAL_ALERT',
            'cooldown'   => 120,
            'max_retries' => 3,
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Escalation Configuration
    |--------------------------------------------------------------------------
    */

    'escalation' => [
        'CRITICAL_ALERT' => [
            'notify'      => ['ops-manager', 'sre-lead', 'platform-oncall'],
            'channel'     => 'pagerduty',
            'description' => 'Automated remediation failed or anomaly persists. Immediate human intervention required.',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | File Paths
    |--------------------------------------------------------------------------
    */

    'incidents_file' => storage_path('aiops/incidents.json'),
    'responses_file' => storage_path('aiops/responses.json'),
];
