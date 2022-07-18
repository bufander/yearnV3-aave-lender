from brownie import reverts, accounts, VaultV3
from constants import SMS_ADDRESS
import pytest


def test_strategy_constructor(usdc, vault, strategy):
    assert strategy.name() == "test_strategy"
    assert strategy.asset() == usdc.address
    assert strategy.vault() == vault.address


def test_investable(strategy, gov):
    assert strategy.investable() == (0, 0)
    strategy.setMinDebt(1, {"from": gov})
    assert strategy.investable() == (1, 0)
    strategy.setMaxDebt(2, {"from": gov})
    assert strategy.investable() == (1, 2)


def test_withdrawable_only_with_assets(
    gov, usdc, create_vault_and_strategy, provide_strategy_with_debt
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    assert strategy.withdrawable() == 0

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert strategy.withdrawable() == new_debt
    assert usdc.balanceOf(vault) == 10 ** 12 - new_debt
    assert usdc.balanceOf(strategy) == new_debt


def test_withdrawable_with_assets_and_atokens(
    usdc, create_vault_and_strategy, gov, provide_strategy_with_debt, atoken
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    assert strategy.withdrawable() == 0

    # let´s provide strategy with assets
    new_debt = 1 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert strategy.withdrawable() == new_debt

    # let´s invest them
    strategy.invest()

    assert strategy.withdrawable() == new_debt
    assert usdc.balanceOf(vault) == 10 ** 12 - new_debt
    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == new_debt

    # Update with more debt without investing
    new_new_debt = new_debt + 0.5 * 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_new_debt)

    assert strategy.withdrawable() == new_new_debt
    assert usdc.balanceOf(vault) == 10 ** 12 - new_new_debt
    assert usdc.balanceOf(strategy) == new_new_debt - new_debt
    assert atoken.balanceOf(strategy) == new_debt


def test_total_assets(gov, usdc, create_vault_and_strategy, provide_strategy_with_debt):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    assert strategy.totalAssets() == 0

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert strategy.totalAssets() == new_debt
    assert usdc.balanceOf(vault) == 10 ** 12 - new_debt
    assert usdc.balanceOf(strategy) == new_debt


def test_invest_trigger(create_vault_and_strategy, gov, provide_strategy_with_debt):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    assert strategy.totalAssets() == 0

    assert strategy.investTrigger() == False

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)
    assert strategy.investTrigger()


def test_invest(
    usdc,
    atoken,
    create_vault_and_strategy,
    gov,
    deposit_into_vault,
    provide_strategy_with_debt,
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    with reverts("no funds to invest"):
        strategy.invest()

    # let's provide strategy with assets
    deposit_into_vault(vault, 10 ** 12)
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    total_assets = strategy.totalAssets()
    assert usdc.balanceOf(strategy) == total_assets
    assert atoken.balanceOf(strategy) == 0

    strategy.invest()

    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == total_assets


def test_free_funds_idle_asset(
    usdc, atoken, create_vault_and_strategy, gov, provide_strategy_with_debt
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt
    assert atoken.balanceOf(strategy) == 0
    vault_balance = usdc.balanceOf(vault)

    strategy.freeFunds(9 ** 6, {"from": vault})

    assert usdc.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt
    assert usdc.balanceOf(vault) == vault_balance


def test_free_funds_atokens(
    usdc,
    atoken,
    create_vault_and_strategy,
    gov,
    provide_strategy_with_debt,
    user_interaction,
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == new_debt

    strategy.invest()

    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt
    vault_balance = usdc.balanceOf(vault)

    # Let´s force Aave pool to update
    user_interaction()

    funds_to_free = 9 * 10 ** 11
    strategy.freeFunds(funds_to_free, {"from": vault})

    assert usdc.balanceOf(strategy) == funds_to_free
    # There should be some more atokens than expected due to profit
    assert atoken.balanceOf(strategy) > new_debt - funds_to_free
    assert strategy.totalAssets() >= new_debt
    assert usdc.balanceOf(vault) == vault_balance


def test_loss__reverts(
    usdc, atoken, create_vault_and_strategy, gov, provide_strategy_with_debt
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == new_debt

    with reverts("not sms"):
        strategy.auxCreateLoss(50, {"from": gov})


def test_loss_with_idle_asset(
    usdc, atoken, create_vault_and_strategy, gov, provide_strategy_with_debt
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == new_debt

    sms = accounts.at(SMS_ADDRESS, force=True)

    loss = 0.5 * 10 ** 12
    strategy.auxCreateLoss(loss, {"from": sms})

    assert usdc.balanceOf(strategy) == loss
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == loss


def test_loss_with_atoken(
    usdc,
    atoken,
    create_vault_and_strategy,
    gov,
    provide_strategy_with_debt,
    user_interaction,
):
    vault, strategy = create_vault_and_strategy(gov, 10 ** 12)

    # let's provide strategy with assets
    new_debt = 10 ** 12
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == new_debt

    strategy.invest()

    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt

    # simulate interaction and ensure we update
    user_interaction()

    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) >= new_debt
    assert strategy.totalAssets() >= new_debt

    sms = accounts.at(SMS_ADDRESS, force=True)
    sms_balance = usdc.balanceOf(sms)

    loss = 0.5 * 10 ** 12
    strategy.auxCreateLoss(loss, {"from": sms})
    assert usdc.balanceOf(strategy) == 0
    assert pytest.approx(atoken.balanceOf(strategy), rel=1e-6) == loss
    assert pytest.approx(strategy.totalAssets(), rel=1e-6) == loss
    assert usdc.balanceOf(sms) == sms_balance + loss
