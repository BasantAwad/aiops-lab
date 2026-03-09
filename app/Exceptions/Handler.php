<?php

namespace App\Exceptions;

use Illuminate\Foundation\Exceptions\Handler as ExceptionHandler;
use Illuminate\Validation\ValidationException;
use Illuminate\Database\QueryException;
use Throwable;

class Handler extends ExceptionHandler
{
    /**
     * A list of exception types with their corresponding custom log levels.
     *
     * @var array<class-string<\Throwable>, \Psr\Log\LogLevel::*>
     */
    protected $levels = [
        //
    ];

    /**
     * A list of the exception types that are not reported.
     *
     * @var array<int, class-string<\Throwable>>
     */
    protected $dontReport = [
        //
    ];

    /**
     * A list of the inputs that are never flashed to the session on validation exceptions.
     *
     * @var array<int, string>
     */
    protected $dontFlash = [
        'current_password',
        'password',
        'password_confirmation',
    ];

    /**
     * Centralized error categorization mapping.
     * Required categories: VALIDATION_ERROR, DATABASE_ERROR, TIMEOUT_ERROR, SYSTEM_ERROR, UNKNOWN
     */
    public static function categorizeError(Throwable $e): string
    {
        if ($e instanceof ValidationException) {
            return 'VALIDATION_ERROR';
        }

        if ($e instanceof QueryException) {
            return 'DATABASE_ERROR';
        }

        if ($e instanceof \Symfony\Component\HttpKernel\Exception\HttpException) {
            return 'SYSTEM_ERROR';
        }

        if ($e instanceof \Exception) {
            return 'SYSTEM_ERROR';
        }

        return 'UNKNOWN';
    }

    /**
     * Register the exception handling callbacks for the application.
     */
    public function register(): void
    {
        $this->reportable(function (Throwable $e) {
            //
        });
    }

    public function render($request, Throwable $e)
    {
        if ($request->is('api/*')) {
            $category = self::categorizeError($e);
            $statusCode = 500;

            if ($e instanceof ValidationException) {
                $statusCode = 422;
            } elseif ($e instanceof QueryException) {
                $statusCode = 500;
            } elseif ($this->isHttpException($e)) {
                $statusCode = $e->getStatusCode();
            }

            return response()->json([
                'status' => 'error',
                'message' => $e->getMessage(),
                'error_category' => $category,
            ], $statusCode);
        }

        return parent::render($request, $e);
    }
}
