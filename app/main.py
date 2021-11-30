from flask import Flask, render_template, request, redirect, url_for
from flaskext.markdown import Markdown
import pandas as pd
import json
# Politeia Explorer and Client
from app.peopleofpi import CommentExplorer

comments_path = "data/comments.csv"

app = Flask(__name__)
# Markdown filter
Markdown(app)

@app.route('/')
def index():
    return render_template('index.html')
    # explorer = CommentExplorer(comments_path)
    # comments = explorer.current_season_comments()
    # ranking = explorer.ranking_from_comments(comments).to_dict(orient="records")
    # season_title = "Season: Current Month"
    # return render_template("ranking.html", ranking=ranking, season_title=season_title)

@app.route('/user/<username>')
def user(username):
    explorer = CommentExplorer(comments_path)
    comments = explorer.comments_df
    ranking = explorer.ranking_from_comments(comments)
    user = explorer.search_user_in_ranking(username,ranking)
    if len(user) == 0:
        return render_template("user_not_found.html")
    else:
        users = pd.read_json("data/users.json")
        mask = users['username'] == username
        user = users[mask].to_dict(orient="records")[0]
        # Comments
        comments = explorer.get_user_comments_df(username)
        # Comment Activity
        activity = explorer.create_comments_activity_df(comments)
        activity_chart = explorer.plot_activity_chart(activity)
        explorer.save_chart(activity_chart,username)
        return render_template("user.html",user=user, comments=comments.to_dict(orient="records")[:5])

# SEASONS
@app.route('/current')
def current():
    explorer = CommentExplorer(comments_path)
    comments = explorer.current_season_comments()
    ranking = explorer.ranking_from_comments(comments).to_dict(orient="records")
    season_title = "Season: Current Month"
    return render_template("ranking.html", ranking=ranking, season_title=season_title)

@app.route('/previous')
def previous():
    explorer = CommentExplorer(comments_path)
    comments = explorer.last_season_comments()
    ranking = explorer.ranking_from_comments(comments).to_dict(orient="records")
    season_title = "Season: Previous Month"
    return render_template("ranking.html", ranking=ranking, season_title=season_title)

@app.route('/historical')
def historical():
    explorer = CommentExplorer(comments_path)
    comments = explorer.comments_df
    ranking = explorer.ranking_from_comments(comments).to_dict(orient="records")
    season_title = "Season: Since The Beginning of Pi"
    return render_template("ranking.html", ranking=ranking, season_title=season_title)

# COMMENTS
@app.route('/comments')
def comments():
    start = request.args.get('start')
    end = request.args.get('end')
    start_date = datetime.strptime(start, '"%Y-%m-%d"').date()
    end_date = datetime.strptime(end, '"%Y-%m-%d"').date()
    data = search.filter_comments(start_date, end_date).values.tolist()
    return render_template("comments.html", data=data)

# SEARCH
@app.route('/search')
def search():
    username = request.args.get('username').lower()
    explorer = CommentExplorer(comments_path)
    comments = explorer.comments_df
    ranking = explorer.ranking_from_comments(comments)
    search = explorer.jaro_search_user_in_ranking(username,ranking)
    # check 100%
    mask = search['search_ratio'] > 0.8
    if len(search[mask]) == 1:
        return redirect(url_for('user', username=username))
    else:
        search = search.to_dict(orient="records")
        season_title = f"Found {len(search)} users"
        return render_template("ranking.html", ranking=search, season_title=season_title )

# @app.route('/about')
# def about():
#     return render_template("about.html")
