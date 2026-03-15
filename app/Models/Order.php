<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Order extends Model
{
    use HasFactory;

    // This is for the last lab "lab3,4"
    protected $fillable = ['customer_name', 'amount', 'status'];
}
