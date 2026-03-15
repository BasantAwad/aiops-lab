<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

/**
 * PaymentService contains the business logic for the SOAP operations.
 * It does not extend Controller. It acts as the class exposing SOAP methods natively.
 */
class PaymentService
{
    // This is the last lab "lab3,4"

    /**
     * SOAP Operation: processPayment
     * Handles payment processing business rule.
     */
    public function processPayment($amount)
    {
        if ($amount <= 0) {
            throw new \SoapFault('Server', 'Amount must be greater than 0');
        }

        return [
            'transaction_id' => uniqid('txn_'),
            'status' => 'success'
        ];
    }

    /**
     * SOAP Operation: refundPayment
     */
    public function refundPayment($transactionId)
    {
        return [
            'transaction_id' => $transactionId,
            'status' => 'refunded'
        ];
    }
}

/**
 * PaymentController is a Laravel Controller responsible for capturing HTTP POST
 * requests and passing them directly to PHP's native SOAP Server engine.
 */
class PaymentController extends Controller
{
    /**
     * POST endpoint handler for incoming SOAP requests.
     */
    public function handleSoap(Request $request)
    {
        $options = [
            'uri' => url('/api/v1/soap/payment'),
        ];

        $server = new \SoapServer(null, $options);
        $server->setClass(PaymentService::class);

        ob_start();
        $server->handle();
        $response = ob_get_clean();

        return response($response, 200)->header('Content-Type', 'text/xml');
    }
}
