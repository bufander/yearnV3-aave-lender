import pytest
from constants import ROLES, MAX_INT
from brownie import Contract, accounts

USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
AUSDC_ADDRESS = "0xBcca60bB61934080951369a648Fb03DF4F96263C"
USDC_WHALE_ADDRESS = "0x0A59649758aa4d66E25f08Dd01271e891fe52199"


@pytest.fixture(scope="function")
def strategist(accounts):
    yield accounts[0]


@pytest.fixture(scope="function")
def gov(accounts):
    yield accounts[1]


@pytest.fixture(scope="function")
def usdc():
    return Contract(USDC_ADDRESS)


@pytest.fixture(scope="function")
def atoken():
    return Contract(AUSDC_ADDRESS)


@pytest.fixture(scope="function")
def amount(usdc):
    # Use always 1M
    return 1_000_000 * 10 ** usdc.decimals()


@pytest.fixture(scope="function")
def create_vault(VaultV3, gov):
    def create_vault(asset, governance=gov, deposit_limit=MAX_INT):
        vault = gov.deploy(VaultV3, asset, "VaultV3", "AV", governance, MAX_INT)
        # set vault deposit
        vault.set_deposit_limit(deposit_limit, {"from": gov})

        vault.set_role(
            gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, {"from": gov}
        )
        return vault

    yield create_vault


@pytest.fixture(scope="function")
def vault(gov, usdc, create_vault):
    vault = create_vault(usdc)
    yield vault


@pytest.fixture(scope="function")
def create_strategy(ERC4626Strategy, strategist):
    # TODO: Vault should come from `@jmonteer/yearn-vaultV3`, not from local contract
    def create_strategy(vault):
        strategy = strategist.deploy(
            ERC4626Strategy,
            vault.address,
            "test_strategy",
            "ts",
            strategist.address,
        )
        return strategy

    yield create_strategy


@pytest.fixture(scope="function")
def strategy(gov, usdc, vault, create_strategy):
    strategy = create_strategy(vault)
    yield strategy


@pytest.fixture
def provide_strategy_with_debt():
    def provide_strategy_with_debt(account, strategy, vault, target_debt: int):
        vault.update_max_debt_for_strategy(
            strategy.address, target_debt, {"from": account}
        )
        vault.update_debt(strategy.address, target_debt, {"from": account})

    return provide_strategy_with_debt


@pytest.fixture
def deposit_into_vault(usdc, gov):
    def deposit_into_vault(vault, amount_to_deposit):
        whale = accounts.at(USDC_WHALE_ADDRESS, force=True)
        usdc.approve(vault.address, amount_to_deposit, {"from": whale})
        vault.deposit(amount_to_deposit, whale.address, {"from": whale})

    yield deposit_into_vault


@pytest.fixture
def create_vault_and_strategy(strategy, vault, deposit_into_vault):
    def create_vault_and_strategy(account, amount_into_vault):
        deposit_into_vault(vault, amount_into_vault)
        vault.add_strategy(strategy.address, {"from": account})
        return vault, strategy

    yield create_vault_and_strategy


@pytest.fixture
def user_interaction(strategy, vault, deposit_into_vault):
    def user_interaction():
        # Due to the fact that Aave doesn`t update internal state till new txs are
        # created, we force it by creating a withdraw
        awhale = "0x13873fa4B7771F3492825B00D1c37301fF41C348"
        lp = Contract("0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9")
        lp.withdraw(
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 1e6, awhale, {"from": awhale}
        )

    yield user_interaction
