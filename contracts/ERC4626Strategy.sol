pragma solidity ^0.8.0;

// TODO: import it from '@yearnvaultsv3/contracts'
import {ERC4626BaseStrategy, IERC20} from "./ERC4626BaseStrategy.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import "./interfaces/ILendingPool.sol";
import "./interfaces/ILendingPoolAddressesProvider.sol";
import "./interfaces/IProtocolDataProvider.sol";
import "./interfaces/IVault.sol";

contract ERC4626Strategy is ERC4626BaseStrategy {
    using Math for uint256;

    //    Aux address to be able to control aux methods during tests
    address internal strategyOps;

    IProtocolDataProvider public constant protocolDataProvider =
    IProtocolDataProvider(0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d);

    address public aToken;

    constructor(
        address _vault,
        string memory _strategyName,
        string memory _strategySymbol,
        address _strategyOps
    ) ERC4626BaseStrategy(_vault, IVault(_vault).asset()) ERC20(_strategyName, _strategySymbol) {
        strategyOps = _strategyOps;

        (address _aToken, ,) = protocolDataProvider.getReserveTokensAddresses(
            IVault(_vault).asset()
        );
        aToken = _aToken;
    }

    //    TODO: override function with strategy needs (should return balance of usdc and balance of aave)
    //    function maxWithdraw(address owner) public view override returns (uint256){}

    function maxDeposit(address receiver) public view virtual override returns (uint256 maxAssets){
        maxAssets = 2 ** 256 - 1;
    }

    function _invest() internal override {
        uint256 available_to_invest = balanceOfAsset();
        require(available_to_invest > 0, "no funds to invest");
        _depositToAave(available_to_invest);
    }

    function totalAssets() public view virtual override returns (uint256) {
        return balanceOfAsset() + balanceOfAToken();
    }

    function harvestTrigger() external view override returns (bool) {}

    function investTrigger() external view override returns (bool) {}

    function delegatedAssets()
    external
    view
    override
    returns (uint256 _delegatedAssets)
    {}

    function _protectedTokens()
    internal
    view
    override
    returns (address[] memory _protected)
    {}

    function _freeFunds(uint256 _amount)
    internal
    override
    returns (uint256 _amountFreed)
    {
        uint256 idle_amount = balanceOfAsset();
        if (_amount <= idle_amount) {
            // we have enough idle assets for the vault to take
            _amountFreed = _amount;
        } else {
            // We need to take from Aave enough to reach _amount
            // We run with 'unchecked' as we are safe from underflow
        unchecked {
            _withdrawFromAave(
                Math.min(_amount - idle_amount, balanceOfAToken())
            );
        }
            _amountFreed = balanceOfAsset();
        }
    }

    function _depositToAave(uint256 amount) internal {
        ILendingPool lp = _lendingPool();
        _checkAllowance(address(lp), asset(), amount);
        lp.deposit(asset(), amount, address(this), 0);
    }

    function _withdrawFromAave(uint256 amount) internal {
        ILendingPool lp = _lendingPool();
        _checkAllowance(address(lp), aToken, amount);
        lp.withdraw(asset(), amount, address(this));
    }

    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            IERC20(_token).approve(_contract, 0);
            IERC20(_token).approve(_contract, _amount);
        }
    }

    function _lendingPool() internal view returns (ILendingPool) {
        return
        ILendingPool(
            protocolDataProvider.ADDRESSES_PROVIDER().getLendingPool()
        );
    }

    function balanceOfAToken() internal view returns (uint256) {
        return IERC20(aToken).balanceOf(address(this));
    }

    function balanceOfAsset() internal view returns (uint256) {
        return IERC20(asset()).balanceOf(address(this));
    }
}
