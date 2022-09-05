from brownie import reverts, accounts, VaultV3
import pytest
from constants import REL_ERROR


def test_strategy_constructor(usdc, vault, strategy):
    assert strategy.name() == "test_strategy"
    assert strategy.asset() == usdc.address
    assert strategy.vault() == vault.address


def test_withdrawable_only_with_assets(
    gov, usdc, create_vault_and_strategy, provide_strategy_with_debt, amount
):
    vault, strategy = create_vault_and_strategy(gov, amount)
    assert strategy.maxWithdraw(vault) == 0

    # let's provide strategy with assets
    new_debt = amount
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert strategy.maxWithdraw(vault) == new_debt
    assert usdc.balanceOf(vault) == amount - new_debt
    assert usdc.balanceOf(strategy) == new_debt


def test_total_assets(
    gov, usdc, create_vault_and_strategy, provide_strategy_with_debt, amount
):
    vault, strategy = create_vault_and_strategy(gov, amount)

    assert strategy.totalAssets() == 0

    # let's provide strategy with assets
    new_debt = amount
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert strategy.totalAssets() == new_debt
    assert usdc.balanceOf(vault) == amount - new_debt
    assert usdc.balanceOf(strategy) == new_debt

    # let´s invest them
    strategy.invest()

    # total assets should remain as it takes into consideration invested assets
    assert strategy.totalAssets() == new_debt


def test_invest(
    usdc,
    atoken,
    create_vault_and_strategy,
    gov,
    deposit_into_vault,
    provide_strategy_with_debt,
    amount,
):
    vault, strategy = create_vault_and_strategy(gov, amount)

    with reverts("no funds to invest"):
        strategy.invest()

    # let's provide strategy with assets
    deposit_into_vault(vault, amount)
    new_debt = amount
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    total_assets = strategy.totalAssets()
    assert usdc.balanceOf(strategy) == total_assets
    assert atoken.balanceOf(strategy) == 0

    strategy.invest()

    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == total_assets


def test_free_funds_idle_asset(
    usdc, atoken, create_vault_and_strategy, gov, provide_strategy_with_debt, amount
):
    vault, strategy = create_vault_and_strategy(gov, amount)

    # let's provide strategy with assets
    new_debt = amount
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt
    assert atoken.balanceOf(strategy) == 0
    vault_balance = usdc.balanceOf(vault)

    strategy.freeFunds(9 ** 6, {"from": vault})

    assert usdc.balanceOf(strategy) == new_debt
    assert strategy.totalAssets() == new_debt
    assert usdc.balanceOf(vault) == vault_balance


def test_withdrawable_with_assets_and_atokens(
    usdc, create_vault_and_strategy, gov, provide_strategy_with_debt, atoken, amount
):
    vault_balance = amount
    vault, strategy = create_vault_and_strategy(gov, vault_balance)

    assert strategy.maxWithdraw(vault) == 0

    # let´s provide strategy with assets
    new_debt = vault_balance // 2
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    # let´s invest them
    strategy.invest()

    assert pytest.approx(strategy.maxWithdraw(vault), rel=REL_ERROR) == new_debt
    assert usdc.balanceOf(vault) == vault_balance - new_debt
    assert usdc.balanceOf(strategy) == 0
    assert atoken.balanceOf(strategy) == new_debt

    # Update with more debt without investing
    new_new_debt = new_debt + vault_balance // 4
    provide_strategy_with_debt(gov, strategy, vault, new_new_debt)

    # strategy has already made some small profit
    assert (
        pytest.approx(strategy.maxWithdraw(vault), rel=REL_ERROR)
        == vault_balance // 2 + vault_balance // 4
    )
    assert usdc.balanceOf(vault) == vault_balance - new_new_debt
    assert usdc.balanceOf(strategy) == new_new_debt - new_debt
    assert atoken.balanceOf(strategy) >= new_debt


def test_free_funds_atokens(
    usdc,
    atoken,
    create_vault_and_strategy,
    gov,
    provide_strategy_with_debt,
    user_interaction,
    amount,
):
    vault, strategy = create_vault_and_strategy(gov, amount)

    # let's provide strategy with assets
    new_debt = amount
    provide_strategy_with_debt(gov, strategy, vault, new_debt)

    assert usdc.balanceOf(strategy) == new_debt
    assert atoken.balanceOf(strategy) == 0
    assert strategy.totalAssets() == new_debt

    strategy.invest()

    assert usdc.balanceOf(strategy) == 0
    assert pytest.approx(atoken.balanceOf(strategy), rel=REL_ERROR) == new_debt
    assert pytest.approx(strategy.totalAssets(), rel=REL_ERROR) == new_debt
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
