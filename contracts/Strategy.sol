// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.14;
pragma experimental ABIEncoderV2;

import {IERC20} from "@yearnvaultsv3/contracts/test/BaseStrategy.sol";

import "@openzeppelin/contracts/utils/math/Math.sol";

// TODO: import it from '@yearnvaultsv3/contracts'
import {BaseStrategy} from "./BaseStrategy.sol";
import "./interfaces/ILendingPool.sol";

contract Strategy is BaseStrategy {
    //  TODO: Should strategyName be on Base Strategy?
    string internal strategyName;
    uint256 public minDebt;
    uint256 public maxDebt;

    //  TODO: make aToken dynamic to avoid breaking if Aave changes underlying contracts.
    //  Use Aave contracts to get address
    address public aToken = 0xBcca60bB61934080951369a648Fb03DF4F96263C;
    ILendingPool lp = ILendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);

    constructor(address _vault, string memory _strategyName)
        BaseStrategy(_vault)
    {
        strategyName = _strategyName;
    }

    function name() external view override returns (string memory) {
        return strategyName;
    }

    function setMinDebt(uint256 _minDebt) external {
        minDebt = _minDebt;
    }

    function setMaxDebt(uint256 _maxDebt) external {
        maxDebt = _maxDebt;
    }

    function investable() external view override returns (uint256, uint256) {
        return (minDebt, maxDebt);
    }

    function withdrawable()
        external
        view
        override
        returns (uint256 _withdrawable)
    {
        _withdrawable = balanceOfAsset() + balanceOfAToken();
    }

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

    function totalAssets() external view override returns (uint256) {
        return _totalAssets();
    }

    function _totalAssets() internal view returns (uint256) {
        return balanceOfAsset() + balanceOfAToken();
    }

    function _emergencyFreeFunds(uint256 _amountToWithdraw) internal override {
        _withdrawFromAave(Math.min(_amountToWithdraw, balanceOfAToken()));
    }

    function _invest() internal override {
        uint256 available_to_invest = balanceOfAsset();
        require(available_to_invest > 0, "no funds to invest");
        _depositToAave(available_to_invest);
    }

    function _harvest() internal override {}

    function _migrate(address _newStrategy) internal override {}

    function harvestTrigger() external view override returns (bool) {}

    function investTrigger() external view override returns (bool) {
        // Let´s increase threshold to an amount that makes operational sense (>0) to avoid dust tokens
        return balanceOfAsset() > 100;
    }

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

    function _withdrawFromAave(uint256 amount) internal {
        _checkAllowance(address(lp), aToken, amount);
        lp.withdraw(address(asset), amount, address(this));
    }

    function _depositToAave(uint256 amount) internal {
        _checkAllowance(address(lp), address(asset), amount);
        lp.deposit(address(asset), amount, address(this), 0);
    }

    function balanceOfAToken() internal view returns (uint256) {
        return IERC20(aToken).balanceOf(address(this));
    }

    function balanceOfAsset() internal view returns (uint256) {
        return IERC20(asset).balanceOf(address(this));
    }

    // Aux function that will return _amount to SMS without Vault knowing, therefore creating a (virtual) loss
    function auxCreateLoss(uint256 _amount) external {
        require(
            msg.sender == 0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7,
            "not sms"
        );
        require(_amount <= _totalAssets(), "not enough assets");
        uint256 total_idle = balanceOfAsset();
        if (_amount > total_idle) {
            _withdrawFromAave(_amount - total_idle);
        }
        IERC20(asset).transfer(msg.sender, _amount);
    }
}
