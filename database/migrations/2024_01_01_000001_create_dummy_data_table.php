<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        if (!Schema::hasTable('dummy_data')) {
            Schema::create('dummy_data', function (Blueprint $table) {
                $table->id();
                $table->string('name');
                $table->string('value')->nullable();
                $table->timestamps();
            });

            // Seed some initial data
            \Illuminate\Support\Facades\DB::table('dummy_data')->insert([
                ['name' => 'sensor_1', 'value' => '23.5', 'created_at' => now(), 'updated_at' => now()],
                ['name' => 'sensor_2', 'value' => '18.2', 'created_at' => now(), 'updated_at' => now()],
                ['name' => 'sensor_3', 'value' => '42.0', 'created_at' => now(), 'updated_at' => now()],
            ]);
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('dummy_data');
    }
};
