<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

use App\Models\Order;

class OrderController extends Controller
{
    // This is the last lab "lab3,4"

    public function index()
    {
        $orders = Order::paginate(10);
        return response()->json($orders, 200);
    }

    public function show($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        return response()->json($order, 200);
    }

    public function store(Request $request)
    {
        $validatedData = $request->validate([
            'customer_name' => 'required|string|max:255',
            'amount' => 'required|numeric|min:0.01',
        ]);

        $order = Order::create([
            'customer_name' => $validatedData['customer_name'],
            'amount' => $validatedData['amount'],
            'status' => 'pending', // Default status
        ]);

        return response()->json($order, 201);
    }

    public function update(Request $request, $id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        $validatedData = $request->validate([
            'customer_name' => 'sometimes|string|max:255',
            'amount' => 'sometimes|numeric|min:0.01',
            'status' => 'sometimes|in:pending,paid,failed',
        ]);

        $order->update($validatedData);

        return response()->json($order, 200);
    }

    public function destroy($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        $order->delete();

        return response()->json(null, 204);
    }

    public function pay($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        try {
            $options = [
                'location' => url('/api/v1/soap/payment'),
                'uri' => url('/api/v1/soap/payment'),
                'trace' => 1
            ];

            $client = new \SoapClient(null, $options);

            // Call the SOAP method processPayment
            $result = $client->processPayment($order->amount);

            // If successful
            $order->update(['status' => 'paid']);

            return response()->json([
                'message' => 'Payment successful',
                'transaction_id' => $result['transaction_id'] ?? null,
                'order' => $order
            ], 200);

        } catch (\SoapFault $e) {
            $order->update(['status' => 'failed']);

            return response()->json([
                'message' => 'Payment failed',
                'error' => $e->getMessage(),
                'order' => $order
            ], 400);
        }
    }
}
