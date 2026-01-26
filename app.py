from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "" 


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(10), default='user')
    playlists = db.relationship('Playlist', backref='owner', lazy=True)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    artist = db.Column(db.String(150), nullable=False)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('PlaylistItems', backref='parent_playlist', cascade="all, delete-orphan")

class PlaylistItems(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'), nullable=False)
    song = db.relationship('Song')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_total_songs():
    total = Song.query.count()
    return dict(total_songs_count=total)


@app.route('/')
@login_required
def index():
    songs = Song.query.all()
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', songs=songs, user_playlists=user_playlists)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        flash("LOGIN FAILED: CHECK CREDENTIALS")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add_song_to_db():
    if current_user.role != 'admin':
        return "Access Denied", 403
    title = request.form.get('title')
    artist = request.form.get('artist')
    if title and artist:
        new_song = Song(title=title, artist=artist)
        db.session.add(new_song)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/create_playlist', methods=['POST'])
@login_required
def create_playlist():
    name = request.form.get('playlist_name')
    if name:
        new_playlist = Playlist(name=name, user_id=current_user.id)
        db.session.add(new_playlist)
        db.session.commit()
    return redirect(url_for('manage_playlists'))

@app.route('/my_collections')
@login_required
def manage_playlists():
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('my_playlists.html', playlists=playlists)

@app.route('/add_to_playlist', methods=['POST'])
@login_required
def add_to_playlist():
    song_id = request.form.get('song_id')
    playlist_id = request.form.get('playlist_id')
    if song_id and playlist_id:
        new_item = PlaylistItems(playlist_id=playlist_id, song_id=song_id)
        db.session.add(new_item)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/playlist/<int:playlist_id>')
@login_required
def view_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return "Access Denied", 403
    return render_template('playlist_detail.html', playlist=playlist)

@app.route('/remove_item/<int:item_id>')
@login_required
def remove_item(item_id):
    item = PlaylistItems.query.get_or_404(item_id)
    playlist_id = item.playlist_id
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('view_playlist', playlist_id=playlist_id))

@app.route('/delete/<int:id>')
@login_required
def delete_song(id):
    if current_user.role == 'admin':
        song = Song.query.get_or_404(id)
        PlaylistItems.query.filter_by(song_id=id).delete()
        db.session.delete(song)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/clear_all')
@login_required
def clear_all():
    if current_user.role == 'admin':
        PlaylistItems.query.delete()
        Song.query.delete()
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_playlist/<int:playlist_id>')
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return "Access Denied", 403
    db.session.delete(playlist)
    db.session.commit()
    return redirect(url_for('manage_playlists'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='boss').first():
            db.session.add(User(username='boss', password='123', role='admin'))
            db.session.add(User(username='student', password='123', role='user'))
            db.session.commit()
    app.run(debug=True)