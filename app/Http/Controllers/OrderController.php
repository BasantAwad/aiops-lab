<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

use App\Models\Order;

class OrderController extends Controller
{
    /**
     * GET /api/v1/orders
     * Retrieves a paginated list of all orders.
     */
    public function index()
    {
        $orders = Order::paginate(10);
        return response()->json($orders, 200);
    }

    /**
     * GET /api/v1/orders/{id}
     * Retrieves a single order by its ID.
     */
    public function show($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        return response()->json($order, 200);
    }

    /**
     * POST /api/v1/orders
     * Creates a new order.
     */
    public function store(Request $request)
    {
        // Validate the incoming JSON payload
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

    /**
     * PUT /api/v1/orders/{id}
     * Updates an existing order.
     */
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

    /**
     * DELETE /api/v1/orders/{id}
     * Deletes an order from the database.
     */
    public function destroy($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        $order->delete();

        return response()->json(null, 204);
    }

    /**
     * POST /api/v1/orders/{id}/pay
     * Integration endpoint: The REST Service calls the SOAP payment service
     * to process an order's payment.
     */
    public function pay($id)
    {
        $order = Order::find($id);

        if (!$order) {
            return response()->json(['message' => 'Order not found'], 404);
        }

        try {
            // For now, simulate SOAP call - in production this would call the actual SOAP service
            if ($order->amount <= 0) {
                throw new \Exception('Amount must be greater than 0');
            }

            // Simulate successful payment
            $transactionId = uniqid('txn_');
            
            $order->update(['status' => 'paid']);

            return response()->json([
                'message' => 'Payment successful',
                'transaction_id' => $transactionId,
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
