import requests
import pandas as pd
import json
from datetime import datetime
from jellyfish import jaro_distance
import matplotlib.pyplot as plt


"""

Politeia Client Class

Politeia Client automates interaction with the politeiawww API
It has methods to get comments, proposals and users.

"""
class PoliteiaClient:
    def __init__(self, api):
        self.api = api

    def get_proposal_comments(self, proposal_token):
        r = requests.get(f"{self.api}/proposals/{proposal_token}/comments")
        proposal = requests.get(f"{self.api}/proposals/{proposal_token}").json()['proposal']
        print(f"[SUCCESS]: Got '{proposal['name']}' by {proposal['username']}")
        return r.json()

    def get_proposal_comments_votes_by_user_df(self, proposal_token):
        proposal_comments = self.get_proposal_comments(proposal_token)
        df = pd.DataFrame(proposal_comments['comments'])
        # Save raw dataframe
        by_user = df.drop(columns=['timestamp']).groupby('username')
        comments_votes = by_user.sum()
        return comments_votes

    def get_proposal_comments_votes_df(self, proposal_token):
        print(f"[UPDATING]: Getting details from proposal {proposal_token}")
        proposal_comments = self.get_proposal_comments(proposal_token)
        df = pd.DataFrame(proposal_comments['comments'])
        return df

    def get_all_proposal_tokens(self):
        proposal_list = []
        print(f'[UPDATING]: Getting latest proposals from {self.api}/proposals/vetted')
        latest = requests.get(f"{self.api}/proposals/vetted").json()['proposals']
        while len(latest) > 0:
            for each in latest:
                proposal_list.append(each['censorshiprecord']['token'])
            if len(latest) == 20:
                last_proposal_token = latest[-1]['censorshiprecord']['token']
                print(f'[UPDATING]: Getting proposals after: {last_proposal_token}')
                latest = requests.get(f"{self.api}/proposals/vetted"+f"?after={last_proposal_token}").json()['proposals']  
            else:
                print('[FINISH] No more proposals to get.')
                break
        print('[REPORT]: Got '+str(len(proposal_list))+' proposals from '+ f"{self.api}/proposals/vetted")
        return proposal_list

    # USER METHODS
    def get_user_id(self, username):
        r = requests.get(f"https://proposals.decred.org/api/v1/users?username={username}").json()
        if r['totalmatches'] > 0:
            user_id = r['users'][0]['id']
            return user_id
        else:
            print(f"[ERROR]: Username '{username}' not found.")
            return None

    def get_user_details(self,user_id):
        user = requests.get(f"https://proposals.decred.org/api/v1/user/{user_id}").json()
        print(user)
        user = user['user']
        
        username = user['username']
        isadmin = user['isadmin']
        user_pastkeys = []
        for identity in user['identities']:
            if identity['isactive']:
                user_pubkey = identity['pubkey']
            else:
                user_pastkeys.append(identity['pubkey'])
        user_details = {"username": username,
                        "id": user_id,
                        "isadmin": isadmin,
                        "pubkey": user_pubkey,
                        "pastkeys": user_pastkeys}
        return user_details

    def get_user_proposals(self,user_id):
        proposals = requests.get(f"https://proposals.decred.org/api/v1/user/proposals?userid={user_id}").json()['proposals']
        print(proposals)
        return proposals
        
"""
Comment Explorer Class

The explorer has methods that aid in data analisis, visualization and filters.
It allows the creation of seasons, rankings and searching for a particular user in a ranking.

"""
class CommentExplorer:
    def __init__(self,comments_path):
        self.comments_df = self.load_comments_df(comments_path)
        print(f"Loaded comments data from {comments_path}")


    # LOAD COMMENTS
    def load_comments_df(self, comments_path):
        df = pd.read_csv(comments_path)    
        df['datetime'] = df['timestamp'].map(lambda x: pd.Timestamp(int(x), unit="s"))
        df['year'] = pd.DatetimeIndex(df['datetime']).year
        df['month'] = pd.DatetimeIndex(df['datetime']).month
        df['day'] = pd.DatetimeIndex(df['datetime']).day
        return df
    
    
    # RANKINGS
    def ranking_from_comments(self, comments_df):
        comment_count = comments_df.groupby(['username']).size().to_frame()
        comment_count['username'] = comment_count.index
        comment_count = comment_count.reset_index(drop=True)
        df = comments_df
        df = df.groupby("username").sum()
        df = df.sort_values("resultvotes",ascending=False)
        df = df.drop(columns=["Unnamed: 0", "parentid","commentid","year","month","day","timestamp"])
        df['username'] = df.index
        df = df.reset_index(drop=True)
        df['rank'] = df.index.map(lambda x: x + 1)
        df = df[["rank","username","resultvotes","upvotes","downvotes","censored"]]
        df['comment_count'] = pd.merge(df, comment_count, left_on="username", right_on="username")[0]
        return df


    # FILTER BY USER
    def get_user_comments_dict(self,username,max=5):
        is_user = self.comments_df['username']==username
        user_df = self.comments_df[is_user]
        comments = user_df.sort_values('datetime',ascending=False).to_dict(orient='records')
        return comments

    def get_user_comments_df(self,username,max=5):
        is_user = self.comments_df['username'] == username
        user_df = self.comments_df[is_user]
        comments = user_df
        return comments.sort_values('datetime',ascending=False)


    # FILTER BY DATE/SEASONS
    def current_season_comments(self):
        now = datetime.now()
        year, month = now.year, now.month
        comments = self.get_season_comments(year, month)
        return comments

    def last_season_comments(self):
        now = datetime.now()
        year, month = now.year, now.month - 1
        if month == 0:
            month = 12
            year = year - 1
        comments = self.get_season_comments(year, month)
        return comments
    
    def get_season_comments(self, year, month):
        comments_df = self.comments_df
        comments_df = comments_df[comments_df['year'] == year]
        comments_df = comments_df[comments_df['month'] == month]
        return comments_df.sort_values('datetime',ascending=False)

    def get_comments_by_month(self,df):
        comments_by_month = df['token'].groupby(pd.Grouper(freq='M')).count()
        return comments_by_month

    def get_latest_comments(self,df,max=5):
        latest_comments = df.iloc[:max]
        return(latest_comments)
    

    # SEARCH
    def search_user_in_ranking(self,user,ranking):
        user = ranking.loc[ranking['username'] == user]
        return user

    def jaro_search_user_in_ranking(self,user,ranking):
        ranking['search_ratio'] = ranking.username.map(lambda x: jaro_distance(user, x))
        ranking = ranking.sort_values("rank", ascending=True)
        mask = ranking['search_ratio'] >= 0.65
        ranking = ranking.loc[mask]
        return ranking


    # VISUALIZATION
    def create_comments_activity_df(self,comments_df):
        df = pd.DataFrame({'year': comments_df['year'],
                        'month': comments_df['month'],
                        'day': comments_df['day']})
        df = pd.to_datetime(df).value_counts().sort_index()
        index = pd.date_range(start="2018-10-16", end=datetime.today())
        df = df.reindex(index, fill_value=0)
        return df
    
    def plot_activity_chart(self,activity_df):
        activity_df = activity_df.resample("M").sum()
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(activity_df.index, activity_df, label='Comments per Month')
        ax.set_ylabel('Comments per Month')
        ax.legend()
        return fig

    def save_chart(self,fig,chart_name):
        fig.savefig(f'static/img/activity_charts/{chart_name}.png')