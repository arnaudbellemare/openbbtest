# Import required libraries
import streamlit as st
import openbb as obb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # For more complex plots if needed
import warnings
from datetime import datetime

# Suppress specific FutureWarnings from Plotly/Pandas if they become noisy
# warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Constants ---
DEFAULT_TICKER = "AAPL"
# Using CBOE as the default free provider for US Equities (delayed data)
# Change this if you have credentials for another provider (e.g., 'tradier', 'intrinio')
DEFAULT_PROVIDER = "cboe"

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OpenBB Options Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Helper Functions ---
def format_datetime_col(df, col_name):
    """Safely formats a datetime column to string, handling potential errors."""
    if col_name in df.columns:
        try:
            # Convert to datetime, coercing errors, then format
            return pd.to_datetime(df[col_name], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return df[col_name] # Return original if formatting fails
    return None

def safe_get_first(series):
    """Safely get the first element of a series/list if it's not empty."""
    try:
        return series.iloc[0] if not series.empty else None
    except IndexError:
        return None

# --- App Title and Description ---
st.title("📊 OpenBB Comprehensive Options Dashboard")
st.markdown(f"""
Enter a stock ticker symbol to fetch and visualize options data using the OpenBB SDK.
- **Provider Used:** `{DEFAULT_PROVIDER}` (Configure OpenBB providers/credentials for other markets or real-time data).
- **Features:** Filterable Options Chain, Open Interest, Volume, Aggregated OI, and Implied Volatility plots.
""")
st.info(f"Note: Data from '{DEFAULT_PROVIDER}' is typically delayed. Availability of specific fields (like Greeks) depends on the provider.", icon="ℹ️")
st.markdown("---")

# --- User Input Form ---
with st.form("ticker_form"):
    ticker_input = st.text_input("Enter a Ticker Symbol:", DEFAULT_TICKER)
    submitted = st.form_submit_button("Fetch Options Data")

# --- Main Logic: Fetch and Display Data ---
if submitted and ticker_input:
    ticker = ticker_input.strip().upper()
    st.markdown(f"## Options Analysis for: **{ticker}**")

    options_df = pd.DataFrame() # Initialize empty dataframe
    underlying_price = None

    with st.spinner(f"Fetching options chain for {ticker} via {DEFAULT_PROVIDER}..."):
        try:
            # --- Fetch Options Chain Data ---
            options_chain_result = obb.derivatives.options.chains(symbol=ticker, provider=DEFAULT_PROVIDER)

            # --- Convert to DataFrame and Clean ---
            if hasattr(options_chain_result, "to_df") and options_chain_result.results:
                options_df = options_chain_result.to_df()

                if not options_df.empty:
                    # Attempt to get underlying price from the result (provider dependent)
                    if 'underlying_price' in options_df.columns:
                       underlying_price = safe_get_first(options_df['underlying_price'].dropna())
                       if underlying_price:
                           st.metric(label=f"{ticker} Underlying Price", value=f"${underlying_price:,.2f}")
                       else:
                           # Fallback if underlying_price column exists but is empty/NaN
                           st.markdown(f"_(Underlying price not available from {DEFAULT_PROVIDER} for {ticker})_")


                    # Standardize and Clean Columns
                    numeric_cols = [
                        'strike', 'open_interest', 'volume', 'implied_volatility',
                        'bid', 'ask', 'last_price', 'underlying_price',
                        'delta', 'gamma', 'theta', 'vega', 'rho'
                    ]
                    for col in numeric_cols:
                         if col in options_df.columns:
                             options_df[col] = pd.to_numeric(options_df[col], errors='coerce')

                    # Handle dates (convert to string for selectbox consistency)
                    if 'expiration' in options_df.columns:
                        options_df['expiration'] = pd.to_datetime(options_df['expiration'], errors='coerce').dt.strftime('%Y-%m-%d')
                        options_df.dropna(subset=['expiration'], inplace=True) # Remove rows where expiration conversion failed
                    else:
                         st.warning("Column 'expiration' not found. Filtering/Analysis by expiration unavailable.", icon="⚠️")

                    # Format other datetime columns if they exist
                    for dt_col in ['last_trade_time', 'bid_time', 'ask_time']:
                         if dt_col in options_df.columns:
                            options_df[dt_col] = format_datetime_col(options_df, dt_col)

                else:
                    st.warning(f"Provider '{DEFAULT_PROVIDER}' returned no options contract data for ticker '{ticker}'. The ticker might be invalid or have no listed options.", icon="⚠️")

            else:
                 st.warning(f"Could not fetch or parse options chain data from '{DEFAULT_PROVIDER}' for '{ticker}'.", icon="⚠️")
                 # Optional: Print raw result for debugging
                 # st.write("Raw provider result:", options_chain_result)


        except Exception as e:
            st.error(f"An error occurred while fetching data for {ticker} using provider '{DEFAULT_PROVIDER}':", icon="🚨")
            st.error(f"{type(e).__name__}: {str(e)}")
            st.info("Check ticker validity, network connection, provider status, or OpenBB credentials (if required for the provider).")
            # st.exception(e) # Uncomment for detailed traceback


    # --- Process and Display Data if DataFrame is populated ---
    if not options_df.empty and 'expiration' in options_df.columns:

        # --- Expiration Date Selector ---
        available_expirations = sorted(options_df['expiration'].unique())
        if available_expirations:
            selected_expiration = st.selectbox(
                "**Select Expiration Date:**",
                options=available_expirations,
                index=min(len(available_expirations) - 1, 2), # Default near-term
                key=f"expiration_filter_{ticker}"
            )
            # Filter DataFrame by selected expiration
            filtered_df = options_df[options_df['expiration'] == selected_expiration].sort_values(by=['strike', 'option_type']).copy()
        else:
            st.warning("No valid expiration dates found in the data.", icon="⚠️")
            selected_expiration = None
            filtered_df = pd.DataFrame() # Empty if no valid expirations

        # --- Display Filtered Options Chain Table ---
        if not filtered_df.empty:
            st.subheader(f"Options Chain for {selected_expiration}")
            # Define columns to display (check if they exist)
            core_cols = ['strike', 'option_type', 'bid', 'ask', 'last_price', 'volume', 'open_interest']
            iv_col = ['implied_volatility'] if 'implied_volatility' in filtered_df.columns else []
            greeks_cols = [col for col in ['delta', 'gamma', 'theta', 'vega'] if col in filtered_df.columns]
            time_cols = ['last_trade_time'] if 'last_trade_time' in filtered_df.columns else []

            display_cols = core_cols + iv_col + greeks_cols + time_cols
            existing_display_cols = [col for col in display_cols if col in filtered_df.columns]

            # Format numbers for display
            format_dict = {
                'strike': '{:.2f}', 'bid': '{:.2f}', 'ask': '{:.2f}', 'last_price': '{:.2f}',
                'volume': '{:,.0f}', 'open_interest': '{:,.0f}',
                'implied_volatility': '{:.2%}', # Format as percentage
                'delta': '{:.3f}', 'gamma': '{:.4f}', 'theta': '{:.3f}', 'vega': '{:.3f}'
            }
            existing_format_dict = {k: v for k, v in format_dict.items() if k in existing_display_cols}

            st.dataframe(filtered_df[existing_display_cols].style.format(existing_format_dict), use_container_width=True)

            # --- Visualizations for Selected Expiration ---
            st.subheader(f"Visualizations for {selected_expiration}")
            col1, col2 = st.columns(2)

            # Plot 1: Open Interest by Strike
            with col1:
                if 'strike' in filtered_df.columns and 'open_interest' in filtered_df.columns and 'option_type' in filtered_df.columns:
                    try:
                        fig_oi = px.bar(
                            filtered_df, x='strike', y='open_interest', color='option_type',
                            barmode='group', title="Open Interest by Strike",
                            labels={'strike': 'Strike Price', 'open_interest': 'Open Interest', 'option_type': 'Type'},
                            hover_data=['volume', 'bid', 'ask']
                        )
                        # Add line for underlying price if available
                        if underlying_price:
                             fig_oi.add_vline(x=underlying_price, line_width=2, line_dash="dash", line_color="grey", annotation_text="Underlying Price", annotation_position="top left")
                        fig_oi.update_layout(legend_title_text='Type')
                        st.plotly_chart(fig_oi, use_container_width=True)
                    except Exception as plot_ex:
                         st.warning(f"Could not plot Open Interest: {plot_ex}", icon="⚠️")
                else:
                     st.warning("OI plot requires 'strike', 'open_interest', 'option_type'.", icon="⚠️")

            # Plot 2: Volume by Strike
            with col2:
                 if 'strike' in filtered_df.columns and 'volume' in filtered_df.columns and 'option_type' in filtered_df.columns:
                    try:
                        fig_vol = px.bar(
                            filtered_df, x='strike', y='volume', color='option_type',
                            barmode='group', title="Volume by Strike",
                            labels={'strike': 'Strike Price', 'volume': 'Volume', 'option_type': 'Type'},
                            hover_data=['open_interest', 'bid', 'ask']
                        )
                        if underlying_price:
                             fig_vol.add_vline(x=underlying_price, line_width=2, line_dash="dash", line_color="grey", annotation_text="Underlying Price", annotation_position="top left")
                        fig_vol.update_layout(legend_title_text='Type')
                        st.plotly_chart(fig_vol, use_container_width=True)
                    except Exception as plot_ex:
                        st.warning(f"Could not plot Volume: {plot_ex}", icon="⚠️")
                 else:
                     st.warning("Volume plot requires 'strike', 'volume', 'option_type'.", icon="⚠️")


            # Plot 3: Implied Volatility Smile/Skew
            st.markdown("---") # Separator before next plot row
            if 'strike' in filtered_df.columns and 'implied_volatility' in filtered_df.columns and 'option_type' in filtered_df.columns:
                iv_data = filtered_df.dropna(subset=['implied_volatility', 'strike']) # Drop rows where IV or strike is NaN
                if not iv_data.empty:
                     try:
                         fig_iv = px.scatter(
                             iv_data, x='strike', y='implied_volatility', color='option_type',
                             title="Implied Volatility Smile / Skew",
                             labels={'strike': 'Strike Price', 'implied_volatility': 'Implied Volatility', 'option_type': 'Type'},
                             hover_data=['open_interest', 'volume', 'delta'] # Show delta on hover if available
                         )
                         # Add lines connecting points for better visualization
                         fig_iv.update_traces(mode='lines+markers')
                         if underlying_price:
                             fig_iv.add_vline(x=underlying_price, line_width=2, line_dash="dash", line_color="grey", annotation_text="Underlying Price", annotation_position="top left")
                         fig_iv.update_layout(yaxis_tickformat=".1%", legend_title_text='Type') # Format IV axis as percentage
                         st.plotly_chart(fig_iv, use_container_width=True)
                     except Exception as plot_ex:
                         st.warning(f"Could not plot Implied Volatility: {plot_ex}", icon="⚠️")
                else:
                    st.info("No valid Implied Volatility data available for this expiration to plot.", icon="ℹ️")
            else:
                 st.info("Implied Volatility plot requires 'strike', 'implied_volatility', 'option_type'.", icon="ℹ️")


        else:
            # This message shows if filtering resulted in an empty dataframe (e.g., no data for selected expiration)
            st.info(f"No contract data found for the selected expiration: {selected_expiration}", icon="ℹ️")


        # --- Aggregated Open Interest Across All Expirations ---
        st.markdown("---")
        st.subheader(f"Total Open Interest Across All Expirations")
        st.markdown("Sum of open interest for each strike price over *all* fetched contract expiration dates.")

        try:
            # Calculate aggregate from the original, full options_df
            if 'strike' in options_df.columns and 'open_interest' in options_df.columns:
                # Ensure OI is numeric, fill NaNs with 0 for summation
                options_df['open_interest_agg'] = pd.to_numeric(options_df['open_interest'], errors='coerce').fillna(0)
                oi_agg = options_df.groupby('strike', as_index=False)['open_interest_agg'].sum()
                oi_agg = oi_agg[oi_agg['open_interest_agg'] > 0] # Filter out strikes with zero total OI

                if not oi_agg.empty:
                     # Display aggregated data table (optional)
                     # st.dataframe(oi_agg.style.format({'strike': '{:.2f}', 'open_interest_agg': '{:,.0f}'}))

                     # Plot Aggregated OI
                     fig_oi_agg = px.bar(
                         oi_agg.sort_values('strike'), x='strike', y='open_interest_agg',
                         title=f"Total Open Interest by Strike (All Expirations)",
                         labels={'strike': 'Strike Price', 'open_interest_agg': 'Total Open Interest'}
                     )
                     if underlying_price:
                         fig_oi_agg.add_vline(x=underlying_price, line_width=2, line_dash="dash", line_color="grey", annotation_text="Underlying Price", annotation_position="top left")
                     st.plotly_chart(fig_oi_agg, use_container_width=True)

                else:
                     st.info(f"No aggregated open interest data could be calculated for {ticker}.", icon="ℹ️")
            else:
                st.warning("Required columns ('strike', 'open_interest') not found for aggregation.", icon="⚠️")

        except Exception as agg_ex:
             st.warning(f"Could not calculate or plot aggregated open interest: {agg_ex}", icon="⚠️")

    # --- Messages for Empty Initial Fetch or Missing Expiration ---
    elif submitted and ticker: # If submitted but options_df ended up empty or without 'expiration'
         st.warning(f"Could not display options data for '{ticker}'. Check fetch errors/warnings above.", icon="⚠️")
    elif submitted and not ticker_input: # If submitted with no ticker
         st.warning("Please enter a ticker symbol.", icon="⚠️")


# --- Initial State Message ---
elif not submitted:
    st.info("Enter a ticker symbol above and click 'Fetch Options Data' to begin.", icon="👋")

# --- Footer ---
st.markdown("---")
st.markdown("Powered by [OpenBB](https://openbb.co/), [Streamlit](https://streamlit.io/), and [Plotly](https://plotly.com/).")
st.caption(f"Data primarily fetched using the '{DEFAULT_PROVIDER}' provider via OpenBB SDK. Data accuracy and availability depend on the provider.")
