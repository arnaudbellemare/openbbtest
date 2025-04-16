# Import required libraries
import streamlit as st
from openbb import obb
import pandas as pd
import plotly.express as px

# Set up the Streamlit app
st.set_page_config(page_title="Options Dashboard", page_icon="📈", layout="wide")
st.title("📈 Options Dashboard")
st.markdown("""
Enter a stock ticker to view options data. Data is fetched using the OpenBB SDK.
- **Options Chain:** Detailed contract data for a selected expiration date.
- **Total Open Interest:** Aggregated open interest across all expirations for each strike price.
""")
st.markdown("---")

# --- User Input Form ---
with st.form("ticker_form"):
    ticker_input = st.text_input("Enter a Ticker Symbol (e.g., AAPL):", "AAPL")
    submitted = st.form_submit_button("Fetch Options Data")

# --- Data Fetching and Display ---
if submitted and ticker_input:
    ticker = ticker_input.upper()
    st.markdown(f"### Options Data for: **{ticker}**")

    with st.spinner(f"Fetching options data for {ticker}..."):
        try:
            # --- Section 1: Options Chain (Detailed per contract) ---
            st.subheader(f"Options Chain Details")
            options_chain_result = obb.derivatives.options.chains(symbol=ticker)

            # Convert to DataFrame
            if hasattr(options_chain_result, "to_df"):
                options_df = options_chain_result.to_df()
                # Ensure numeric types where expected for plotting/sorting
                for col in ['strike', 'open_interest', 'volume', 'implied_volatility', 'bid', 'ask']:
                     if col in options_df.columns:
                         options_df[col] = pd.to_numeric(options_df[col], errors='coerce')
                # Convert expiration to string for consistent selection
                if 'expiration' in options_df.columns:
                    options_df['expiration'] = options_df['expiration'].astype(str)

            else:
                # Handle cases where conversion isn't straightforward (though unlikely for chains)
                st.warning("Could not convert options chain result to DataFrame.")
                options_df = pd.DataFrame() # Create empty df to avoid errors later

            if not options_df.empty:
                # --- Expiration Date Selector ---
                if 'expiration' in options_df.columns:
                    available_expirations = sorted(options_df['expiration'].unique())
                    selected_expiration = st.selectbox(
                        "Select Expiration Date:",
                        options=available_expirations,
                        index=min(2, len(available_expirations)-1) # Default to a near-term date
                    )
                    # Filter DataFrame by selected expiration
                    filtered_df = options_df[options_df['expiration'] == selected_expiration].copy() # Use .copy() to avoid SettingWithCopyWarning
                else:
                    st.warning("Expiration date column not found in data.")
                    filtered_df = options_df # Use unfiltered if no expiration
                    selected_expiration = "All"

                st.markdown(f"**Displaying Options Chain for {ticker} - Expiration: {selected_expiration}**")
                st.dataframe(filtered_df) # Use st.dataframe for better table display

                # --- Plot: Open Interest vs. Strike for Selected Expiration ---
                if not filtered_df.empty and 'strike' in filtered_df.columns and 'open_interest' in filtered_df.columns:
                    # Separate Calls and Puts for clarity
                    calls = filtered_df[filtered_df['option_type'] == 'call']
                    puts = filtered_df[filtered_df['option_type'] == 'put']

                    # Create figure
                    fig_chain = px.bar(filtered_df, x='strike', y='open_interest',
                                       color='option_type', barmode='group',
                                       title=f"Open Interest by Strike ({selected_expiration})",
                                       labels={'strike': 'Strike Price', 'open_interest': 'Open Interest', 'option_type': 'Type'},
                                       hover_data=['volume', 'implied_volatility', 'bid', 'ask']) # Add more hover info
                    fig_chain.update_layout(xaxis_title="Strike Price", yaxis_title="Open Interest")
                    st.plotly_chart(fig_chain, use_container_width=True)

                    # Optional: Volume Plot
                    # fig_vol = px.bar(filtered_df, x='strike', y='volume',
                    #                  color='option_type', barmode='group',
                    #                  title=f"Volume by Strike ({selected_expiration})",
                    #                  labels={'strike': 'Strike Price', 'volume': 'Volume', 'option_type': 'Type'})
                    # fig_vol.update_layout(xaxis_title="Strike Price", yaxis_title="Volume")
                    # st.plotly_chart(fig_vol, use_container_width=True)

                else:
                    st.warning("Required columns (strike, open_interest, option_type) not found for plotting chain data.")

            else:
                st.warning(f"No options chain data available for {ticker}.")


            # --- Section 2: Total Open Interest (Aggregated across expirations) ---
            st.subheader(f"Total Open Interest Across All Expirations")
            st.markdown("This shows the sum of open interest for each strike price over all available contract expiration dates.")
            try:
                # This specific endpoint might not exist or might require different parameters.
                # Let's calculate it from the full chain if the specific endpoint isn't ideal
                # open_interest_result = obb.derivatives.options.open_interest(symbol=ticker) # Keep original attempt if preferred

                # Alternative: Calculate aggregate from the full chain data
                if not options_df.empty and 'strike' in options_df.columns and 'open_interest' in options_df.columns:
                    oi_agg = options_df.groupby('strike')['open_interest'].sum().reset_index()
                    oi_df = oi_agg
                else:
                    oi_df = pd.DataFrame() # Empty if chain failed

            except Exception as oi_err:
                 st.warning(f"Could not fetch or calculate aggregated open interest: {oi_err}")
                 oi_df = pd.DataFrame()


            # Display aggregated data if available
            if not oi_df.empty:
                st.dataframe(oi_df)

                # --- Plot: Total Open Interest by Strike Price ---
                if 'strike' in oi_df.columns and 'open_interest' in oi_df.columns:
                    fig_oi_agg = px.bar(oi_df, x='strike', y='open_interest',
                                        title=f"Total Open Interest by Strike Price (All Expirations)",
                                        labels={'strike': 'Strike Price', 'open_interest': 'Total Open Interest'})
                    st.plotly_chart(fig_oi_agg, use_container_width=True)
                else:
                    st.warning("Required columns (strike, open_interest) not found for plotting aggregated OI data.")
            else:
                st.info(f"No aggregated open interest data could be generated for {ticker}.")


        except Exception as e:
            st.error(f"An error occurred while fetching data for {ticker}: {e}")
            st.warning("Please ensure the ticker is valid and check your OpenBB provider configuration and credentials.")
            st.exception(e) # Optionally show the full traceback for debugging

else:
    if submitted and not ticker_input:
        st.warning("Please enter a ticker symbol.")
    else:
        st.info("Enter a ticker symbol above and click 'Fetch Options Data' to begin.")


# --- Footer ---
st.markdown("---")
st.markdown("Powered by [OpenBB](https://openbb.co/), [Streamlit](https://streamlit.io/), and [Plotly](https://plotly.com/). Data availability depends on OpenBB's configured providers.")
