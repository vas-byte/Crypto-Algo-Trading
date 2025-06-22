import os
import pandas as pd

dir = 'Data'

# Loop through files ending with USD_1d.csv
for filename in os.listdir(dir):
    if filename.endswith('coinmarketcap.csv'):
        input_path = os.path.join(dir, filename)
        output_path = os.path.join(dir, f'{filename}')

        try:
            # Read CSV with semicolon delimiter
            df = pd.read_csv(input_path, sep=';', quotechar='"')

            # Load the CSV
            df = pd.read_csv(os.path.join(dir,filename), sep=';')

            # Remove any surrounding quotes in datetime fields
            df['timeOpen'] = df['timeOpen'].str.replace('"', '')

            # Convert to datetime object and reformat as YYYY-MM-DD
            df['timeOpen'] = pd.to_datetime(df['timeOpen'], format='%Y-%m-%dT%H:%M:%S.%fZ')
            df['timeOpen'] = df['timeOpen'].dt.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'

            # Select and rename required columns
            df_cleaned = df[['timeOpen', 'open', 'high', 'low', 'close', 'volume', 'marketCap']].copy()

            # Sort by date ascending
            df_cleaned = df_cleaned.sort_values(by='timeOpen')

            # Reset index (optional)
            df_cleaned.reset_index(drop=True, inplace=True)

            # Save to new CSV or print
            df_cleaned.to_csv(os.path.join(dir,filename), index=False)     

        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
