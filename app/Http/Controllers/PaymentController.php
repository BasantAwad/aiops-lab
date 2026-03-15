<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class PaymentService
{
    // This is the last lab "lab3,4"

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

    public function refundPayment($transactionId)
    {
        return [
            'transaction_id' => $transactionId,
            'status' => 'refunded'
        ];
    }
}

class PaymentController extends Controller
{
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
