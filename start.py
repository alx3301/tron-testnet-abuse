from os import listdir
from time import sleep
from tronpy import Tron
from random import choice
from tronpy.keys import PrivateKey
from subprocess import Popen, PIPE
from fake_useragent import UserAgent
from RecaptchaSolver import RecaptchaSolver
from requests.exceptions import ReadTimeout
from DrissionPage.errors import ElementNotFoundError
from DrissionPage import ChromiumPage, ChromiumOptions

tron = Tron(network="shasta")
destination_address = "THpayhWN96EqAKNdZVabkU4vfss4ru5qut"
config = choice([f for f in listdir("ovpn") if f.endswith(".ovpn")])

while True:
    try:
        if config:
            process = Popen([
                "sudo",
                "openvpn",
                "--config",
                f"ovpn/{config}",
                "--auth-user-pass",
                "credentials.txt"
            ], stdout=PIPE, stderr=PIPE, text=True) 

            if any("Initialization Sequence Completed" in line.strip() for line in process.stdout):
                user_agent = UserAgent().random
                driver = ChromiumPage(
                    ChromiumOptions()
                    .incognito(True)
                    .set_user_agent(user_agent))
                recaptcha_solver = RecaptchaSolver(driver)
                private_key = PrivateKey.random()
                address = private_key.public_key.to_base58check_address()
                driver.get("https://shasta.tronex.io/")
                driver.ele("#getCoinAddress").input(address)
                try:
                    recaptcha_solver.solveCaptcha()
                except ElementNotFoundError:
                    driver.close()
                    process.terminate()
                else:
                    driver.ele("#submitGetTestCoinForm").click()
                    if driver.ele("#coinAlertMessage").text == "Successful acquisition of test coins.":
                        while True:
                            try:
                                balance = tron.get_account(address)["balance"]
                                if balance:
                                    transaction = (
                                        tron.trx.transfer(
                                            from_=address,
                                            to=destination_address,
                                            amount=balance
                                        ).build().sign(private_key).broadcast()
                                    )
                                    if transaction["result"]:
                                        print(f"Transaction successful! TxID: {transaction["txid"]}")
                                        break
                                else:
                                    sleep(3)
                            except ReadTimeout:
                                continue
                    driver.close()
                    process.terminate()
    finally:
        process.terminate()