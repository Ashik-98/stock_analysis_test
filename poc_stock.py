import requests
# print(requests.__version__)
import pandas as pd
pd.set_option('display.max_columns', None)    # to display all columns

github_api_url = "https://api.github.com/repos/squareshift/stock_analysis/contents/"
response = requests.get(github_api_url)

# print(response.json())
# print(response.text)
# print(type(response.json()))
files = response.json()
csv_files = [file['download_url'] for file in files if file['name'].endswith('.csv')]
#print(csv_files)

#print(len(csv_files))
csv_file = csv_files.pop() # removes the last element and assigns to csv_file
#print(len(csv_files))
d = pd.read_csv(csv_file)
#print(d)
# print(d.columns) # column names
# print(len(d.columns))
# print(d.head()) # first 5 rows
# print(d.tail()) # last 5 rows
# print(d.shape) # rows,columns
# print(d.describe())

# url = "https://raw.githubusercontent.com/squareshift/stock_analysis/main/A.csv"
# file_name = url.split("/")[-1].replace(".csv", "")  # using this logic to replace A.csv to A (for getting the filenename)
# print(file_name)
dataframes=[]
file_names=[]
for url in csv_files:
    file_name = url.split("/")[-1].replace(".csv", "")
    df = pd.read_csv(url)
    df['Symbol'] = file_name
    dataframes.append(df) # list of elements
    file_names.append(file_name)
# print(file_names)
# print(dataframes)
combined_df = pd.concat(dataframes, ignore_index=True) # puts index into the entire dataframe
#print(combined_df) # to join the dataframes vertically
#print(combined_df.describe())
o_df = pd.merge(combined_df,d,on='Symbol',how='left')
#print(o_df)
result = o_df.groupby("Sector").agg({'open':'mean','close':'mean','high':'max','low':'min','volume':'mean'}).reset_index()
                                                                #after group by index breaks so we give reset index
#print(result)
# print(o_df["timestamp"])
o_df["timestamp"] = pd.to_datetime(o_df["timestamp"]) # changing the data type of timestamp column to datetime (from str)
filtered_df = o_df[(o_df['timestamp'] >= "2021-01-01") & (o_df['timestamp'] <= "2021-05-26")]
#print(filtered_df)
result_time = filtered_df.groupby("Sector").agg({'open':'mean','close':'mean','high':'max','low':'min','volume':'mean'}).reset_index() #reset_index to get the index

list_sector = ["TECHNOLOGY","FINANCE"]
result_time = result_time[result_time["Sector"].isin(list_sector)].reset_index(drop=True)
print(result_time)
path=r"D:\Batch-18 (RRR)\output.csv"   #output is written in the path
result_time.to_csv(path,header=True)
print("Completed")
print("poc completed")