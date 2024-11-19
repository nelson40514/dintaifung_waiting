from requests import post

def getShopStatus(shopId="0001"):
    url = 'https://www.dintaifung.tw/Queue/Home/WebApiTest'
    parameter = {"storeid":shopId}

    res = post(url, data=parameter)

    print(res.json())
    return res.json()

def main():
    getShopStatus("0009")

if __name__ == '__main__':
    main()