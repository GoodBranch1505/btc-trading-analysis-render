<?php
$price_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=jpy";
$price = json_decode(file_get_contents($price_url), true)['bitcoin']['jpy'];

$heroku_url = "https://btc-trading-analysis.herokuapp.com/analyze";
$post_data = ['price' => $price, 'timestamp' => time(), 'btc_count' => 0];
$options = [
    'http' => [
        'method' => 'POST',
        'header' => 'Content-Type: application/json',
        'content' => json_encode($post_data)
    ]
];
file_get_contents($heroku_url, false, stream_context_create($options));
?>