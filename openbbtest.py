# Import required libraries
import streamlit as st
from openbb import obb
import pandas as pd
import plotly.express as px

# Set up the Streamlit app
st.set_page_config(page_title="Options Dashboard", page_icon="📈", layout="wide")
st.title("📈 Options Dashboard for Any Ticker")
st.markdown("Enter a stock ticker to view options data, including the options chain and open interest by strike price.")

# User input for ticker
ticker = st.text_input("Enter a Ticker Symbol (e.g., AAPL):", "AAPL").upper()

# Fetch and display options data when a ticker is entered
if ticker:
    with st.spinner(f"Fetching options data for {ticker}..."):
        try:
            # Section 1: Options Chain
            st.subheader(f"Options Chain for {ticker}")
            options_chain = obb.derivatives.options.chains(symbol=ticker)

            # Convert to DataFrame if necessary
            if hasattr(options_chain, "to_df"):
                options_df = options_chain.to_df()
            else:
                options_df = pd.DataFrame(options_chain)

            # Display the raw options chain data
            if not options_df.empty:
                st.write(options_df)

                # Plot open interest by strike price using Plotly
                if 'strike' in options_df.columns and 'open_interest' in options_df.columns:
                    fig = px.scatter(options_df, x='strike', y='open_interest', 
                                     color='option_type', size='volume', 
                                     title=f"Open Interest by Strike Price for {ticker}",
                                     labels={'strike': 'Strike Price', 'open_interest': 'Open Interest'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Required columns (strike, open_interest) not found in the options chain data.")
            else:
                st.warning("No options chain data available for this ticker.")

            # Section 2: Open Interest by Strike Price
            st.subheader(f"Open Interest by Strike for {ticker}")
            open_interest = obb.derivatives.options.open_interest(symbol=ticker)

            # Convert to DataFrame if necessary
            if hasattr(open_interest, "to_df"):
                oi_df = open_interest.to_df()
            else:
                oi_df = pd.DataFrame(open_interest)

            if not oi_df.empty:
                st.write(oi_df)

                # Plot open interest by strike price
                if 'strike' in oi_df.columns and 'open_interest' in oi_df.columns:
                    fig_oi = px.bar(oi_df, x='strike', y='open_interest', 
                                    title=f"Total Open Interest by Strike Price for {ticker}",
                                    labels={'strike': 'Strike Price', 'open_interest': 'Open Interest'})
                    st.plotly_chart(fig_oi, use_container_width=True)
                else:
                    st.warning("Required columns (strike, open_interest) not found in the open interest data.")
            else:
                st.warning("No open interest data available for this ticker.")

        except Exception as e:
            st.error(f"An error occurred while fetching data for {ticker}: {str(e)}")
            st.write("Please ensure the ticker is valid and that OpenBB supports options data for this symbol.")

# Footer
st.markdown("---")
st.markdown("Powered by [OpenBB](https://openbb.co/), [Streamlit](https://streamlit.io/), and [Plotly](https://plotly.com/). Data availability depends on OpenBB's configured providers.")
