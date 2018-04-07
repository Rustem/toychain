# Fetch Block Count

Gets the number of blocks that are residing in the blockchain storage.

**URL** : `blk/cnt/`

**Example URL** : `http://localhost:65164/34268774b426751444e55786d594e46505459325/blk/cnt` 

**Method** : `GET`

## Success Response

**Code** : `200 OK`

**Content examples**


```json
[valid block count as integer]
```

Blockchain with height = 5 consists of exactly 5 blocks. 

```json
5
```