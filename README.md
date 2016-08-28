# Pool server

This software includes:
* A pool master for miner handling
* A pool controller

## Warning

The software is not well tested and it's a work in progress, use at your own risk.

## Requirements

* golang
* python2
* python2 flask
* python2 requests
* python2 pysqlite3

## Configuration

For first, configure the pool master:

1. Open poolmaster/pool.go
2. Choose a secure key, and replace the one proposed in line 46
3. Set the poolPort at line 46; this will be used by pool miners
4. Set the port of your ethereum daemon at line 47
5. Enter the ethpool.py directory and run ``` ./make_poolmaster.sh ```

Now edit ethpool.py:

1. At line 15, set the previously secure key
2. At line 21, set the pool fee
3. At line 22, set your coinbase address

## Startup

1. Start geth or similar with rpc ``` geth --rpc ```
2. First run ``` ./poolmaster/pool ```
3. Start the pool server with ``` python ethpool.py ```

## Donations
Donations are always welcome:

BTC: 13TRVwiqLMveg9aPAmZgcAix5ogKVgpe4T
ETH: 0x18f081247ad32af38404d071eb8c246cc4f33534
