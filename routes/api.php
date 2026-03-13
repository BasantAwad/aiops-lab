<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ApiController;

/*
|--------------------------------------------------------------------------
| [LAB WORK 1] - API Routes for Telemetry Generation
|--------------------------------------------------------------------------
| These endpoints were built to simulate standard application behavior.
| They are targeted by the traffic_generator.py script to produce
| structured logs and prometheus metrics via the TelemetryMiddleware.
*/

Route::get('/normal', [ApiController::class, 'normal'])->name('api.normal');
Route::get('/slow', [ApiController::class, 'slow'])->name('api.slow');
Route::get('/error', [ApiController::class, 'error'])->name('api.error');
Route::get('/random', [ApiController::class, 'random'])->name('api.random');
Route::get('/db', [ApiController::class, 'db'])->name('api.db');
Route::post('/validate', [ApiController::class, 'validateData'])->name('api.validate');