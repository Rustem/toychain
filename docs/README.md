# Blockchain Node HTTP JSON API

There are two predefined parameters necessary for constructing url sucessfully:

* listening http host ip e.g. `10.0.0.2`
* listening http port e.g. `49985`
* account address e.g. `34268774b426751444e55786d594e46505459325`

Each API endpoint is opened without any authentication since blockchain network is public.

Core url is `http://${host}:{port}/${address}` e.g. `http://10.0.0.2:49985/34268774b426751444e55786d594e46505459325`.
Meaning that every endpoint is relative to this path.

## Endpoints

* [Create Transaction](create_txn.md) : `POST txn/`
* [Fetch Transaction Info](fetch_txn.md): `POST txn/${txn_id}/`
* [Fetch Block Count](fetch_block_count.md) : `GET blk/cnt/`
* [Fetch Block Info](fetch_block_info.md) : `GET blk/${block_number}/`