<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ApiController;

// [LAB WORK 1]

Route::get('/normal', [ApiController::class, 'normal'])->name('api.normal');
Route::get('/slow', [ApiController::class, 'slow'])->name('api.slow');
Route::get('/error', [ApiController::class, 'error'])->name('api.error');
Route::get('/random', [ApiController::class, 'random'])->name('api.random');
Route::get('/db', [ApiController::class, 'db'])->name('api.db');
Route::post('/validate', [ApiController::class, 'validateData'])->name('api.validate');

use App\Http\Controllers\OrderController;
use App\Http\Controllers\PaymentController;

Route::prefix('v1')->group(function () {
    Route::apiResource('orders', OrderController::class);
    Route::post('orders/{order}/pay', [OrderController::class, 'pay']);


    Route::post('soap/payment', [PaymentController::class, 'handleSoap']);
});