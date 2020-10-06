import time

def test_proxy_earn(accounts, Token, Contract, StrategyCurveYVoterProxy, StrategyProxy):
    # NOTE: This person has a ton of DAI, but flash loans could be used instead
    hacker = accounts[-1]

    # Grab all code from the chain
    andre = accounts[-3]
    multisig = accounts[-2]
    # sleeps between calls to avoid etherscan rate limit
    crv = Contract("0x45F783CCE6B7FF23B2ab2D70e416cdb7D6055f51")
    time.sleep(1)
    ycrv = Token.at("0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8")
    time.sleep(1)
    dai = Token.at("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    time.sleep(1)
    ydai = Contract("0x16de59092dAE5CcF4A1E6439D611fd0653f0Bd01")
    time.sleep(1)
    vault = Contract("0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c")
    time.sleep(1)
    controller = Contract(vault.controller())
    time.sleep(1)
    curveYCRVVoter = Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")

    ## How it works:
    ## Deploy fixed StrategyProxy
    ## Set new StrategyProxy.address as proxy on StrategyCurveYVoterProxy
    ## Deploy StrategyCurveYVoterProxy as strategy
    ## controller.approveStrategy("0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", strategy, {"from": multisig})
    ## controller.setStrategy("0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", strategy, {"from": multisig})
    ## Set proxy strategy on voter
    ## curveYCRVVoter.setStrategy(strategyProxy, {"from": multisig})
    ## Gives control on proxy to governance
    ## strategyProxy.setGovernance(multisig, {"from": deployer})
    ## Set strategy on proxy strategy (for withdrawals)
    ## strategyProxy.approveStrategy(strategy, {"from": multisig})


    strategyProxy = andre.deploy(StrategyProxy)
    print("new strategyProxy:", strategyProxy) # Use this address for StrategyCurveYVoterProxy under proxy
    strategy = andre.deploy(StrategyCurveYVoterProxy, controller)

    controller.approveStrategy(
        "0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", strategy, {"from": multisig},
    )
    controller.setStrategy(
        "0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8", strategy, {"from": multisig}, # Change strategy to vulnerableStrategy to steal funds
    )
    curveYCRVVoter.setStrategy(
        strategyProxy, {"from": multisig} # Set proxy strategy on voter
    )
    strategyProxy.setGovernance(multisig, {"from": andre}) # Gives control on proxy to governance
    strategyProxy.approveStrategy(
        strategy, {"from": multisig} # Set strategy on proxy strategy (for withdrawals)
    )

    # Convert DAI to yCRV
    dai.approve(ydai, 2 ** 256 - 1, {"from": hacker})
    ydai.deposit(dai.balanceOf(hacker), {"from": hacker})
    ydai.approve(crv, 2 ** 256 - 1, {"from": hacker})
    crv.add_liquidity([ydai.balanceOf(hacker), 0, 0, 0], 0, {"from": hacker})
    ycrv.approve(vault, 2 ** 256 - 1, {"from": hacker})

    before = ycrv.balanceOf(hacker)
    print(before)
    print(ycrv.balanceOf(hacker))
    while ycrv.balanceOf(hacker) - before >= 0:
        print("Vault's assets", vault.balance() // 10 ** vault.decimals(), "yCRV")
        print(
            "Hacker's balance", ycrv.balanceOf(hacker) // 10 ** ycrv.decimals(), "yCRV"
        )
        vault.deposit(ycrv.balanceOf(hacker) // 2, {"from": hacker})  # Deposit half
        vault.earn(
            {"from": hacker} # default limit to test fix 
            # {"from": hacker, "gas_limit": 250000} # 250000 limit throws invalid opcode ## Add invalid_opcode catch Test
        )  # Purposely-underfund gas (fails to update)
        vault.deposit(
            ycrv.balanceOf(hacker), {"from": hacker}
        )  # Deposit the other half
        vault.earn({"from": hacker})  # Big swing
        vault.withdraw(vault.balanceOf(hacker), {"from": hacker})  # Profit!

    assert ycrv.balanceOf(hacker) - before <= 0
