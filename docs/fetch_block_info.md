# Fetch Block Information

Extracts block information with state from the blockchain storage.

**URL** : `blk/${block_number}/`

**Example URL** : `http://localhost:65189/34268774b426751444e55786d594e46505459325/blk/4` 

**Method** : `GET`

## Success Response

**Code** : `200 OK`

**Content examples**

For a User with ID 1234 on the local database where that User has saved an
email address and name information.

```json
{
  "number": "[valid integer]",
  "hash_parent": "[valid parent block has as hex-encoded text]",
  "body": "[list of transactions objects]",
  "nonce": "[valid integer]",
  "data": "[plain text]",
  "id": "[valid block hash as plain text]",
  "difficulty": "[corresponds to genesis configuration as integer]",
  "hash_state": "[hash state as hex-encoded text]",
  "hash_txns": "[hash of transactions as hex-encoded text]",
  "reward": "[block reward as integer"]",
  "time": "[timestamp as float]",
  "coinbase": "[coinbase address as hex-encoded text]",
  "state": "[map of accounts where key is address and value is object]"
}
```

For a block number 4 the following information has been returned.

```json
{
  "number": 4,
  "hash_parent": "0000c34a9a6045a7cb15f1cf6c80ff84b9423c0a18b5240aec51fe3ed8e89b3b",
  "body": [
    {
      "id": "b0d7715998ccbec88fed86c49cb5bca4a4b6a5cb72e6f25bdea470a9a6738c98",
      "from": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b426751444e55786d594e465054593251394d75384c33532b3055566b780a666c37344e437338437734553458586655534a5a33656572354f59595355644c4636557a515266383054766e355036434d6f414b31353530316a4851516e705a0a536c35596f70786e6d646b55435366455332416641426966687842564d6978632f3870724b37746d772f7839692b305954574868462f6f4a36685363425231420a52736a61684f4a6a4e306c444a78745a4277494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a",
      "amount": 30,
      "signature": "RL+ZQMsJZWIhjgnpf92cEIQFBVo7RcZalwkf0B5ded5Tkgb3r9m+DxsRye10f8q0b4wk7BB3dIkYHa7L82W8LZ+fqlbEE4eLLB+fONqnGFUduxM7AQ3Xph+wM3OJ6ZjCRn8MLOSUN5RQjBmCAIwqE/Sa5lXw6JKj+9x1DMFxuCM=",
      "time": 1523101618.693394,
      "data": "43j9pZCiaiv8WfX",
      "number": 7,
      "to": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b42675144695a674c4d635441797a7553786a2f3031744c5830346972570a6b795436384d62446a36573046636b67736655615137514f684451526f30325073755363504d30335a546a4c54714e4c526c366b634d73634553637a7a5775440a31687078556b4b58784a6f4b6d2f39647874726469525a66444e615856596e6944414d444c6749744f5147547137472b4c724452364376674e4275576561562b0a6d54643251693465515950315835394c4151494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a "
    },
    {
      "id": "03a56272f9daa15cac5fc9e797049b695fa7fb10a52782c674048da1d1833c93",
      "from": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b426751444e55786d594e465054593251394d75384c33532b3055566b780a666c37344e437338437734553458586655534a5a33656572354f59595355644c4636557a515266383054766e355036434d6f414b31353530316a4851516e705a0a536c35596f70786e6d646b55435366455332416641426966687842564d6978632f3870724b37746d772f7839692b305954574868462f6f4a36685363425231420a52736a61684f4a6a4e306c444a78745a4277494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a",
      "amount": 30,
      "signature": "tdyk7DI5570jkfkppZ9BFWOmrqIQCvE39tHnYkqKy4p5ivmK8GO9qAgoMy4dzMk51arrguMeA4H0DUfbGOk81XNwAsWGiVoblk0sr8nLzj8lSGgjmyBpcm8Bt9eI67psnM/NCnjfvwLpwxkkeuuobqW2WJk7YvF5wY6Fm8BIJe4=",
      "time": 1523101619.030986,
      "data": "8TLLNKRA0dLcJGb",
      "number": 8,
      "to": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b42675144695a674c4d635441797a7553786a2f3031744c5830346972570a6b795436384d62446a36573046636b67736655615137514f684451526f30325073755363504d30335a546a4c54714e4c526c366b634d73634553637a7a5775440a31687078556b4b58784a6f4b6d2f39647874726469525a66444e615856596e6944414d444c6749744f5147547137472b4c724452364376674e4275576561562b0a6d54643251693465515950315835394c4151494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a "
    },
    {
      "id": "af1b6040c2b3c412ca5de184f83463fd7474e061d7157859617eea2d4cb0c2f7",
      "from": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b426751444e55786d594e465054593251394d75384c33532b3055566b780a666c37344e437338437734553458586655534a5a33656572354f59595355644c4636557a515266383054766e355036434d6f414b31353530316a4851516e705a0a536c35596f70786e6d646b55435366455332416641426966687842564d6978632f3870724b37746d772f7839692b305954574868462f6f4a36685363425231420a52736a61684f4a6a4e306c444a78745a4277494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a",
      "amount": 30,
      "signature": "RCEzXzAI9oVRrF1FEU5NGA0dEEplvCFhsQvxPSXohMjt5THszsMXRjGR/oBsCBFTd9fMv84wGzIhcttUKH1m9nbN716pRNhca7Ou1Il4KJFvB9fv/0S9a60AxOo0MM7HyaiDh/QtugTR8zoNfiVxxdYggJuIrsJpdwDzFjLc3Tc=",
      "time": 1523101619.333426,
      "data": "EI357fPRrnU9Sdi",
      "number": 9,
      "to": "2d2d2d2d2d424547494e205055424c4943204b45592d2d2d2d2d0a4d4947644d413047435371475349623344514542415155414134474c4144434268774b42675144695a674c4d635441797a7553786a2f3031744c5830346972570a6b795436384d62446a36573046636b67736655615137514f684451526f30325073755363504d30335a546a4c54714e4c526c366b634d73634553637a7a5775440a31687078556b4b58784a6f4b6d2f39647874726469525a66444e615856596e6944414d444c6749744f5147547137472b4c724452364376674e4275576561562b0a6d54643251693465515950315835394c4151494245513d3d0a2d2d2d2d2d454e44205055424c4943204b45592d2d2d2d2d0a "
    }
  ],
  "nonce": 57893,
  "data": "DWv6xPfaxQCxH1v",
  "id": "0000831226445940138cc40d761c961aa4de873c4bedafcf0ef9f372c41a7212",
  "difficulty": 4,
  "hash_state": "55ec1bdc05f04e08467aec92ffc2402edebb601c6085057f4a813ccf4fc01792",
  "hash_txns": "89583158d303e30dff1fd1ffe22165431c9ed2ff165b422be6b790ccf8226635",
  "reward": 100,
  "time": 1523101619.336644,
  "coinbase": "34268774b426751444f6346517a72676631302f6",
  "state": {
    "34268774b426751444f6346517a72676631302f6": {
      "address": "34268774b426751444f6346517a72676631302f6",
      "nonce": 0,
      "balance": 10000100
    },
    "34268774b426751444e55786d594e46505459325": {
      "address": "34268774b426751444e55786d594e46505459325",
      "nonce": 9,
      "balance": 9729
    },
    "34268774b42675144695a674c4d635441797a755": {
      "address": "34268774b42675144695a674c4d635441797a755",
      "nonce": 0,
      "balance": 570
    }
  }
}
```