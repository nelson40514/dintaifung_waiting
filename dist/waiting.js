fetch("https://www.dintaifung.tw/Queue/Home/WebApiTest", {
    "headers": {
        "accept": "*/*",
        "accept-language": "en;q=0.9",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "priority": "u=0, i",
        "sec-ch-ua": "\"Brave\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.dintaifung.tw/Queue/",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    },
    //   "body": "storeid=0009",
    "method": "POST"
}).then(response => {
    console.log(response);
    return response.json();
}).then(data => {
    // [
    //     {
    //       store_id: '0009',
    //       wait_time: '45',
    //       num_1: '1053',
    //       num_2: '3030',
    //       num_3: '5011',
    //       num_4: '7003',
    //       togo_numbers: '0021,0081,0088,84-1,51-1',
    //       last_time: 0
    //     }
    //   ]
    console.log(data);
}).catch(error => {
    console.log(error);
});
export {};
