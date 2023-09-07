#!/usr/bin/env python
# coding: utf-8

# In[1]:


from googleapiclient.discovery import build
import pandas as pd
import streamlit as st
from pymongo import MongoClient
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from datetime import datetime


# In[2]:


# Set your YouTube API key
api_key = 'AIzaSyBcA0LNFhyyxk_C62o2xaS0ngsrItLm5AE'
youtube = build('youtube', 'v3', developerKey=api_key)


# In[3]:


# Function to get channel data
def get_channel_data(youtube, channel_id):
    channel_data = youtube.channels().list(
        part='snippet,contentDetails,statistics',
        id=channel_id
    )
    response = channel_data.execute()
    data = dict(
        channel_name=response['items'][0]["snippet"]["title"],
        channel_id=response['items'][0]['id'],
        subscribers=response['items'][0]["statistics"]["subscriberCount"],
        views=response['items'][0]["statistics"]["viewCount"],
        total_videos=response['items'][0]["statistics"]["videoCount"],
        playlist_id=response['items'][0]["contentDetails"]["relatedPlaylists"]["uploads"],
        channel_description=response['items'][0]['snippet']['description']
    )

    return data


# In[4]:


# Function to get video IDs from playlist
def get_video_ids(youtube, playlist_id):
    request = youtube.playlistItems().list(
        part='contentDetails',
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()

    video_ids = []

    for item in response['items']:
        video_ids.append(item['contentDetails']['videoId'])

    next_page_token = response.get('nextPageToken')

    while next_page_token:
        request = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])

        next_page_token = response.get('nextPageToken')

    return video_ids


# In[5]:


def convert_duration(duration_string):
    # By calling timedelta() without any arguments, the duration
    # object is initialized with a duration of 0 days, 0 seconds, and 0 microseconds. Essentially, it sets the initial duration to zero.
    duration_string = duration_string[2:]  # Remove "PT" prefix
    duration = timedelta()
    
    # Extract hours, minutes, and seconds from the duration string
    if 'H' in duration_string:
        hours, duration_string = duration_string.split('H')
        duration += timedelta(hours=int(hours))
    
    if 'M' in duration_string:
        minutes, duration_string = duration_string.split('M')
        duration += timedelta(minutes=int(minutes))
    
    if 'S' in duration_string:
        seconds, duration_string = duration_string.split('S')
        duration += timedelta(seconds=int(seconds))
    
    # Format duration as H:MM:SS
    duration_formatted = str(duration)
    if '.' in duration_formatted:
        hours, rest = duration_formatted.split(':')
        minutes, seconds = rest.split('.')
        duration_formatted = f'{int(hours)}:{int(minutes):02d}:{int(seconds):02d}'
    else:
        duration_formatted = duration_formatted.rjust(8, '0')
    
    return duration_formatted


# In[6]:


def convert_timestamp(timestamp):
    datetime_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    formatted_time = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


# In[7]:


# Function to get video details
def get_video_details(youtube, video_ids):
    all_video_stats = []

    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids[i:i+50])
        )
        
        req = youtube.videos().list(
            part='contentDetails',
            id=','.join(video_ids[i:i+50])
        )
        response = request.execute()
        res = req.execute()

        for video, vid in zip(response['items'], res['items']):
            video_stats = {
                'title': video['snippet']['title'],
                'video_id': video['id'],
                'channel_id': video['snippet']['channelId'],
                'published_date':convert_timestamp(video['snippet']['publishedAt']),
                'video_description': video['snippet']['description'],
                'views': video['statistics']['viewCount'],
                'likes': video['statistics']['likeCount'],
                'comments': video['statistics']['commentCount'],
                'time_duration': convert_duration(vid['contentDetails']['duration'])
            }
            
            all_video_stats.append(video_stats)
            
    return all_video_stats


# In[8]:


def get_comment_details(youtube, video_ids):
    all_video_stats = []

    for video_id in video_ids:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id
        )
        response = request.execute()

        # Process the response and append the comment details to all_video_stats
        for comments in response['items']:
            comment = dict(
                comment_id=comments["id"],
                comment_text=comments["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                comment_author=comments["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                comment_published_at=convert_timestamp(comments["snippet"]["topLevelComment"]["snippet"]["publishedAt"]),
                video_id= video_id[0]
            )
            all_video_stats.append(comment)

    return all_video_stats


# In[9]:


def get_all_dada(youtube, channel_id,video_ids):
                # Get the channel data
            channel_data = get_channel_data(youtube, channel_id)
            st.subheader('Channel Data')
            st.write(channel_data)

           # Get the video details
            video_details = get_video_details(youtube, video_ids)
            st.subheader('Video Details')
            st.write(video_details)

            # Comment data
            comment_details = get_comment_details(youtube, video_ids)
            st.subheader('Comments')
            st.write(comment_details)

            data_file = {'ch_id': channel_data,
                         'video_info': video_details,
                         'comments': comment_details}

            return data_file


# In[10]:


# Connect to MongoDB and Function to store data in MongoDB
def store_information_in_mongodb(get_all_info):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['youtubedata']
    collection = db['channel_info']
    collection.insert_one(get_all_info)
    


# In[11]:


# Connect to MySQL
def create_tables():
    
    import mysql.connector
    import pymysql
# Connect to MySQL
    mysql_connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Dhinesh!1')
        #autocommit=True)

    mysql_cursor = mysql_connection.cursor()

    mysql_cursor.execute("CREATE DATABASE IF NOT EXISTS youtubedata")
    mysql_cursor.execute("USE youtubedata")
    
    create_channel_table = '''
        CREATE TABLE IF NOT EXISTS channel_data (
        channel_name VARCHAR(100),
        channel_id VARCHAR(500) PRIMARY KEY,
        subscribers INT,
        views_count INT,
        total_videos INT,
        playlist_id VARCHAR(100),
        channel_description TEXT
    );
'''
    mysql_cursor.execute(create_channel_table)
    mysql_cursor.fetchall()  # Consume the result

    create_video_table = '''
        CREATE TABLE IF NOT EXISTS video_details (
        title VARCHAR(500),
        video_id VARCHAR(255) PRIMARY KEY,
        channel_id VARCHAR(500),
        published_date DATE,
        video_description TEXT,
        views INT,
        likes INT,
        comments VARCHAR(500),
        time_duration VARCHAR(200)
    );
'''
    mysql_cursor.execute(create_video_table)
    mysql_cursor.fetchall()  # Consume the result

    create_comment_table = '''
        CREATE TABLE IF NOT EXISTS comment_details (
        comment_id INT PRIMARY KEY,
        comment_text TEXT,
        comment_author TEXT,
        comment_published_at DATE,
        video_id VARCHAR(255)
        
        );
'''
    mysql_cursor.execute(create_comment_table)
    mysql_cursor.fetchall()  # Consume the result

    mysql_connection.commit()
# Close the cursor and the connection
    mysql_cursor.close()
    mysql_connection.close()
    
    return True  


# In[12]:


def store_information_in_sql():
    # Connect to MySQL
    mysql_connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Dhinesh!1',
        database='youtubedata'
    )
    
    mysql_cursor = mysql_connection.cursor()

    client = MongoClient('mongodb://localhost:27017/')
    db = client['youtubedata']
    collection = db['channel_info']
    
    mycollection = db['channel_info']
    
    document_names = []
    
    for i in mycollection.find():
        document_names.append(i)
    
    mongodata = pd.DataFrame(document_names)

    chennal_file = mongodata['ch_id']
    video_file = mongodata['video_info']
    comments = mongodata['comments']
    
    channel_dat = []
    
    for i in range(len(chennal_file)):
        channel_dataframe = chennal_file[i]
        channel_dat.append(channel_dataframe)
    channel_dataframe = pd.DataFrame(channel_dat)
    
    channel_id_playlist_id = channel_dataframe[['channel_id', 'playlist_id']]
    
    video_dat = []
    for i in range(len(video_file)):
        all_videos = video_file[i]
        video_dat.extend(all_videos)
    video_info = pd.DataFrame(video_dat)
    
    comment_dat = []
    for i in range(len(comments)):
        all_comments = comments[i]
        comment_dat.extend(all_comments)
    comment_data = pd.DataFrame(comment_dat)
    
    # Inserting channel details
    insert_channeldetails = '''INSERT IGNORE INTO channel_data (channel_name, channel_id, subscribers, views_count, total_videos, playlist_id,channel_description) VALUES (%s, %s, %s, %s, %s, %s, %s)'''
    values = channel_dataframe.values.tolist()
    mysql_cursor.executemany(insert_channeldetails, values)
    
    # Inserting video details
    insert_videodetails = '''INSERT IGNORE INTO video_details (title, video_id, channel_id, published_date, video_description, views, likes, comments, time_duration)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
'''
    values = video_info.values.tolist()
    mysql_cursor.executemany(insert_videodetails, values)

    # Inserting comment details
    insert_commentdetails = '''INSERT IGNORE INTO comment_details (comment_id, comment_text, comment_author, comment_published_at, video_id) VALUES (%s, %s, %s, %s, %s)'''
    values = comment_data.values.tolist()
    mysql_cursor.executemany(insert_commentdetails, values)
    
    mysql_connection.commit()
    
    # Close the cursor and the connection
    mysql_cursor.close()
    mysql_connection.close()
    


# In[13]:


menu = ["Channel information", "SQL Data Warehouse","Channel queries"]

choice = st.sidebar.selectbox("Select an option", menu)
if choice=='Channel information':
    st.title("Welcome to the YouTube Data Warehousing App")
    channel=st.text_input("Enter channel_id")
    submit=st.button('submit')

    if submit:
        c=get_channel_data(youtube,channel)
        #st.dataframe(c)
        playlist_id=c['playlist_id']
        v=get_video_ids(youtube,playlist_id)
        # vds=[]
        # for i in v:
        #     vds.append(i[0])
        # st.write(vds)
        vd= get_video_details(youtube, v)
        #st.dataframe(vd)
        cd=get_comment_details(youtube,v)
        #st.dataframe(cd)
        all_data_info=get_all_dada(youtube, channel,v)
        st.write(all_data_info)
        st.header(':blue[Data Collection]')
        store_information_in_mongodb(all_data_info)
        st.write('successfull inserted to mongodb')
        
def app_sql():
    
    if choice=="SQL Data Warehouse":
        import_to_sql=st.button('Import_to_SQL')
        st.write("click the button to import data")
        if import_to_sql:
            store_information_in_sql()
            st.write('inserted succcesfully')
            # st.experimental_rerun()

            
def main():
    if choice=="Channel queries":
        st.subheader("Select a  question!!")
        ques1 = '1.	What are the names of all the videos and their corresponding channels?'
        ques2 = '2.	Which channels have the most number of videos, and how many videos do they have?'
        ques3 = '3.	What are the top 10 most viewed videos and their respective channels?'
        ques4 = '4.	How many comments were made on each video, and what are their corresponding video names?'
        ques5 = '5.	Which videos have the highest number of likes, and what are their corresponding channel names?'
        ques6 = '6.	What is the total number of likes and dislikes for each video, and what are their corresponding video names?'
        ques7 = '7.	What is the total number of views for each channel, and what are their corresponding channel names?'
        ques8 = '8.	What are the names of all the channels that have published videos in the year 2022?'
        ques9 = '9.	What is the average duration of all videos in each channel, and what are their corresponding channel names?'
        ques10 = '10.Which videos have the highest number of comments, and what are their corresponding channel names?'
        question = st.selectbox('Queries!!',(ques1,ques2,ques3,ques4,ques5,ques6,ques7,ques8,ques9,ques10))
        clicked4 = st.button("MYSQL")
        
        if clicked4:
            mysql_connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Dhinesh!1',
            database='youtubedata')
            
            mysql_cursor = mysql_connection.cursor()
           
            mysql_cursor.execute("SHOW DATABASES")
            databases = mysql_cursor.fetchall() 
            mysql_cursor.execute("USE youtubedata")
            
            if question == ques1:
                query = "select title,channel_name FROM video_details AS A INNER JOIN channel_data AS B ON A.channel_id=B.channel_id;"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques2:
                query = "select channel_name,total_videos from channel_data where total_videos=(SELECT MAX(total_videos) FROM channel_data);"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques3:
                query = "select title,views,channel_name from video_details as a inner join channel_data as b on a.channel_id=b.channel_id order by views desc limit 10;"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques4:
                query = "select title,comments from video_details order by comments desc;"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques5:
                query = "select title,likes,channel_name from video_details as a inner join channel_data as b on a.channel_id=b.channel_id where likes=(select max(likes) from video_details);"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques6:
                query = "select likes,title from video_details order by likes asc;"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques7:
                query = "select channel_name,sum(views) as total_video_count from video_details as a inner join channel_data as b on a.channel_id=b.channel_id group by b.channel_name order by sum(views);"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques8:
                query = "select published_date,channel_name from video_details as a inner join channel_data as b on a.channel_id=b.channel_id WHERE published_date BETWEEN '2022-01-01' AND '2022-12-31';"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques9:
                query = "select channel_name,avg(time_duration) from video_details as a inner join channel_data as b on a.channel_id=b.channel_id group by b.channel_name;"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            elif question == ques10:
                query = "select title,comments,channel_name from video_details as a inner join channel_data as b on a.channel_id=b.channel_id where comments=(select max(comments) from video_details);"
                mysql_cursor.execute(query)
                results =mysql_cursor.fetchall()
                st.dataframe(results)
            
#  the code structure using if __name__ == '__main__': allows you to define and execute 
#  specific code (e.g., functions, initialization tasks, etc.) that should only be executed when the script is run directly as the main program
# When a script is imported as a module, the Python interpreter executes all the top-level code 
# in that script, including function definitions and other initialization tasks. Placing the main program code
# inside the if __name__ == '__main__': block ensures that it will only be
# executed when the script is run directly, avoiding unintended execution when the script is imported as a module.
            
            
if __name__ == '__main__':
    main()
    app_sql()
                


# In[ ]:




