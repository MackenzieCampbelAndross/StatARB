"""Initial schema creation

Revision ID: 001_initial
Revises:
Create Date: 2026-09-17 14:36:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create instruments table
    op.create_table(
        'instruments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('instrument_type', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('listed_date', sa.DateTime(), nullable=True),
        sa.Column('delisted_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_instrument_sector', 'instruments', ['sector'])
    op.create_index('idx_instrument_exchange', 'instruments', ['exchange'])
    op.create_index('idx_instrument_active', 'instruments', ['is_active'])

    # Create prices table
    op.create_table(
        'prices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('adjusted_close', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_price_symbol_timestamp', 'prices', ['symbol', 'timestamp'])
    op.create_index('idx_price_timestamp', 'prices', ['timestamp'])
    op.create_index('ix_prices_symbol', 'prices', ['symbol'])

    # Create pairs table
    op.create_table(
        'pairs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('symbol_a', sa.String(), nullable=False),
        sa.Column('symbol_b', sa.String(), nullable=False),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('correlation', sa.Float(), nullable=True),
        sa.Column('correlation_lookback', sa.Integer(), nullable=True),
        sa.Column('correlation_period', sa.DateTime(), nullable=True),
        sa.Column('coint_p_value', sa.Float(), nullable=True),
        sa.Column('hedge_ratio', sa.Float(), nullable=True),
        sa.Column('half_life', sa.Float(), nullable=True),
        sa.Column('adf_p_value', sa.Float(), nullable=True),
        sa.Column('adf_statistic', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pair_symbols', 'pairs', ['symbol_a', 'symbol_b'])
    op.create_index('idx_pair_active', 'pairs', ['is_active'])
    op.create_index('idx_pair_correlation', 'pairs', ['correlation'])
    op.create_index('ix_pairs_symbol_a', 'pairs', ['symbol_a'])
    op.create_index('ix_pairs_symbol_b', 'pairs', ['symbol_b'])

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pair_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('price_a', sa.Float(), nullable=False),
        sa.Column('price_b', sa.Float(), nullable=False),
        sa.Column('spread', sa.Float(), nullable=False),
        sa.Column('z_score', sa.Float(), nullable=False),
        sa.Column('signal', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=True),
        sa.Column('hedge_ratio', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('entry_reason', sa.String(), nullable=True),
        sa.Column('exit_reason', sa.String(), nullable=True),
        sa.Column('data_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_signal_pair_timestamp', 'signals', ['pair_id', 'timestamp'])
    op.create_index('idx_signal_timestamp', 'signals', ['timestamp'])
    op.create_index('idx_signal_type', 'signals', ['signal'])
    op.create_index('ix_signals_pair_id', 'signals', ['pair_id'])

    # Create backtests table
    op.create_table(
        'backtests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('initial_capital', sa.Float(), nullable=False),
        sa.Column('final_capital', sa.Float(), nullable=True),
        sa.Column('total_return', sa.Float(), nullable=True),
        sa.Column('cagr', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('volatility', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('num_trades', sa.Integer(), nullable=True),
        sa.Column('avg_trade_return', sa.Float(), nullable=True),
        sa.Column('avg_holding_period', sa.Float(), nullable=True),
        sa.Column('turnover', sa.Float(), nullable=True),
        sa.Column('gross_pnl', sa.Float(), nullable=True),
        sa.Column('net_pnl', sa.Float(), nullable=True),
        sa.Column('entry_z_score', sa.Float(), nullable=False),
        sa.Column('exit_z_score', sa.Float(), nullable=False),
        sa.Column('stop_z_score', sa.Float(), nullable=False),
        sa.Column('holding_period', sa.Integer(), nullable=False),
        sa.Column('transaction_cost', sa.Float(), nullable=False),
        sa.Column('slippage', sa.Float(), nullable=False),
        sa.Column('position_sizing', sa.String(), nullable=True),
        sa.Column('correlation_threshold', sa.Float(), nullable=True),
        sa.Column('coint_p_value', sa.Float(), nullable=True),
        sa.Column('training_window', sa.Integer(), nullable=True),
        sa.Column('testing_window', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_backtest_dates', 'backtests', ['start_date', 'end_date'])
    op.create_index('idx_backtest_status', 'backtests', ['status'])
    op.create_index('idx_backtest_created', 'backtests', ['created_at'])

    # Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('backtest_id', sa.String(), nullable=False),
        sa.Column('pair_id', sa.String(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('exit_date', sa.DateTime(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('entry_z_score', sa.Float(), nullable=False),
        sa.Column('exit_z_score', sa.Float(), nullable=False),
        sa.Column('holding_period', sa.Integer(), nullable=False),
        sa.Column('entry_price_a', sa.Float(), nullable=False),
        sa.Column('entry_price_b', sa.Float(), nullable=False),
        sa.Column('exit_price_a', sa.Float(), nullable=False),
        sa.Column('exit_price_b', sa.Float(), nullable=False),
        sa.Column('hedge_ratio', sa.Float(), nullable=False),
        sa.Column('position_size', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('return_pct', sa.Float(), nullable=False),
        sa.Column('transaction_cost', sa.Float(), nullable=True),
        sa.Column('slippage', sa.Float(), nullable=True),
        sa.Column('is_train', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_backtest_trade_backtest', 'backtest_trades', ['backtest_id'])
    op.create_index('idx_backtest_trade_pair', 'backtest_trades', ['pair_id'])
    op.create_index('idx_backtest_trade_dates', 'backtest_trades', ['entry_date', 'exit_date'])
    op.create_index('ix_backtest_trades_backtest_id', 'backtest_trades', ['backtest_id'])
    op.create_index('ix_backtest_trades_pair_id', 'backtest_trades', ['pair_id'])

    # Create research_experiments table
    op.create_table(
        'research_experiments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entry_z_score', sa.Float(), nullable=False),
        sa.Column('exit_z_score', sa.Float(), nullable=False),
        sa.Column('stop_z_score', sa.Float(), nullable=False),
        sa.Column('holding_period', sa.Integer(), nullable=False),
        sa.Column('transaction_cost', sa.Float(), nullable=False),
        sa.Column('slippage', sa.Float(), nullable=False),
        sa.Column('position_sizing', sa.String(), nullable=True),
        sa.Column('correlation_threshold', sa.Float(), nullable=True),
        sa.Column('coint_p_value', sa.Float(), nullable=True),
        sa.Column('training_window', sa.Integer(), nullable=True),
        sa.Column('testing_window', sa.Integer(), nullable=True),
        sa.Column('total_return', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('cagr', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('num_trades', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_research_created', 'research_experiments', ['created_at'])
    op.create_index('idx_research_status', 'research_experiments', ['status'])


def downgrade() -> None:
    op.drop_index('idx_research_status', table_name='research_experiments')
    op.drop_index('idx_research_created', table_name='research_experiments')
    op.drop_table('research_experiments')

    op.drop_index('ix_backtest_trades_pair_id', table_name='backtest_trades')
    op.drop_index('ix_backtest_trades_backtest_id', table_name='backtest_trades')
    op.drop_index('idx_backtest_trade_dates', table_name='backtest_trades')
    op.drop_index('idx_backtest_trade_pair', table_name='backtest_trades')
    op.drop_index('idx_backtest_trade_backtest', table_name='backtest_trades')
    op.drop_table('backtest_trades')

    op.drop_index('idx_backtest_created', table_name='backtests')
    op.drop_index('idx_backtest_status', table_name='backtests')
    op.drop_index('idx_backtest_dates', table_name='backtests')
    op.drop_table('backtests')

    op.drop_index('ix_signals_pair_id', table_name='signals')
    op.drop_index('idx_signal_type', table_name='signals')
    op.drop_index('idx_signal_timestamp', table_name='signals')
    op.drop_index('idx_signal_pair_timestamp', table_name='signals')
    op.drop_table('signals')

    op.drop_index('ix_pairs_symbol_b', table_name='pairs')
    op.drop_index('ix_pairs_symbol_a', table_name='pairs')
    op.drop_index('idx_pair_correlation', table_name='pairs')
    op.drop_index('idx_pair_active', table_name='pairs')
    op.drop_index('idx_pair_symbols', table_name='pairs')
    op.drop_table('pairs')

    op.drop_index('ix_prices_symbol', table_name='prices')
    op.drop_index('idx_price_timestamp', table_name='prices')
    op.drop_index('idx_price_symbol_timestamp', table_name='prices')
    op.drop_table('prices')

    op.drop_index('idx_instrument_active', table_name='instruments')
    op.drop_index('idx_instrument_exchange', table_name='instruments')
    op.drop_index('idx_instrument_sector', table_name='instruments')
    op.drop_table('instruments')
