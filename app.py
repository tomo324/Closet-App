import os,cv2, tempfile, uuid, requests, base64
from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
from flask_migrate import Migrate
from google.cloud import storage
from settings import GCS_BUCKET_NAME, SQLALCHEMY_DATABASE_URI
import PIL.Image
from io import BytesIO
import io


# アップロードされる拡張子の制限
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])

app = Flask(__name__)
app.config["DEBUG"] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///closet.db'

# 本番環境ではこれを使う
# app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# LoginManagerをインスタンス化
login_manager = LoginManager()
# Flaskアプリと紐づけ
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.String(100))
    category = db.Column(db.Enum('tops', 'bottoms'))
    user_id = db.Column(db.Integer, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id')) # Imageモデルとの関連性を定義


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    object_name = db.Column(db.String(256), nullable=False)  # GCSのオブジェクト名
    public_url = db.Column(db.String(256), nullable=False)  # Google Cloud Storageの公開URL
    user_id = db.Column(db.Integer, nullable=False)
    post = db.relationship('Post', backref='image', uselist=False) # Postとの逆参照を定義


class OutfitImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tops_image_id = db.Column(db.Integer, nullable=False)
    bottoms_image_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

# サービスアカウントのjsonファイルのパス
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "closet-app-388006-79ea106aacf3.json"

# Google Cloud Storageクライアントのインスタンス化
gcs = storage.Client()


def make_background_transparent(image_data):
    # 画像データをデコードして読み込む
    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    height, width = image.shape[:2]

    # 画像をRGBA形式に変換する
    rgba_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)

    # GrabCutアルゴリズムを使用して背景と前景を分離する
    mask = np.zeros(image.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (1, 1, width-1, height-1)
    cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    # マスクを適用して背景を透過させる
    rgba_image[:, :, 3] = mask2 * 255

    # 画像をBGRAからRGBAに変換する
    rgba_image = cv2.cvtColor(rgba_image, cv2.COLOR_BGRA2RGBA)

    #pngフォーマットにエンコードしてからbase64にエンコードする
    _, encoded_image = cv2.imencode('.png', rgba_image)
    base64_image = base64.b64encode(encoded_image).decode('utf-8')
    return base64_image


@app.route('/index', methods=['GET'])
@login_required
def index():
    if request.method == 'GET':
        user = current_user
        username = user.username
        # 現在ログインしているユーザーが登録した情報を取得
        tops = Post.query.filter_by(user_id=user.id).filter_by(category='tops').all()
        bottoms = Post.query.filter_by(user_id=user.id).filter_by(category='bottoms').all()
        images = Image.query.filter_by(user_id=user.id).all()
        # image.idをキー、エンコードされた画像データをバリューとする辞書を作成
        encoded_images_dict = {image.id: base64.b64encode(requests.get(image.public_url).content).decode('utf-8') for image in images}

        return render_template('index.html', encoded_images_dict=encoded_images_dict, tops=tops, bottoms=bottoms, username=username)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    cropped_image = None
    if request.method == 'GET':
        return render_template('create.html', cropped_image=cropped_image)
    else:
        # 画像のトリミングを行う
        title = request.form.get('title')
        detail = request.form.get('detail')
        category = request.form.get('category')

        # トリミングされた画像データを受け取る
        cropped_image_base64 = request.form.get('crop-result') 
        if not cropped_image_base64:
            flash('ファイルがありません')
            return redirect(request.url)
        
        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image_base64 = cropped_image_base64.replace("data:image/jpeg;base64,", "")

        # base64文字列からバイトデータに変換
        cropped_image_data = base64.b64decode(cropped_image_base64)

        # トリミングされた画像データを一時ファイルに保存
        temp_image_file = tempfile.NamedTemporaryFile(delete=False)
        temp_image_file.write(cropped_image_data)
        temp_image_file.close()

        # 一時ファイルのパスをセッションに保存
        session['image_path'] = temp_image_file.name
        session['title'] = title
        session['detail'] = detail
        session['category'] = category
        return render_template('create.html', title=title, detail=detail, category=category, cropped_image=cropped_image_base64)


# トリミングされた画像を透過して保存
@app.route('/save_rgba', methods=['POST'])
@login_required
def save_rgba():
    if request.method == 'POST':
        #一時ファイルから画像データを読み込む
        with open(session['image_path'], 'rb') as f:
            cropped_image = f.read()
        title = session.get('title')
        detail = session.get('detail')
        category = session.get('category')
        user_id = current_user.id

        # 画像を透過し、base64エンコードされたデータとして受け取る
        rgba_image = make_background_transparent(cropped_image)

        # Base64からバイトデータに変換
        rgba_image_data = base64.b64decode(rgba_image)

        # バイトデータからImageオブジェクトに変換
        rgba_image = PIL.Image.open(io.BytesIO(rgba_image_data))

        # 一時的なバッファに画像を保存
        buffer = BytesIO()
        rgba_image.save(buffer, format="WEBP", quality=10, lossless=False)

        # バッファからバイトデータを取得
        buffer.seek(0)
        rgba_image_bytes = buffer.read()

        # UUIDを生成
        filename = str(uuid.uuid4()) + '.webp'  # 拡張子もwebpに変更

        # GCSのバケットにアップロードする
        bucket = gcs.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(rgba_image_bytes)

        blob.make_public()

        # 透過済みの画像をデータベースに保存する
        new_image = Image(object_name=filename, public_url=blob.public_url, user_id=user_id)
        db.session.add(new_image)
        db.session.commit()

        new_post = Post(title=title, detail=detail, category=category, user_id=user_id, image_id=new_image.id)
        db.session.add(new_post)
        db.session.commit()


        # ホームページにリダイレクトする
        return redirect(url_for('index'))


# トリミングされた画像を透過せずに保存
@app.route('/save_cropped', methods=['POST'])
@login_required
def save_cropped():
    if request.method == 'POST':
        cropped_image = request.form.get('image-src-input')
        title = session.get('title')
        detail = session.get('detail')
        category = session.get('category')
        user_id = current_user.id

        # データ部分だけを取り出してデコードする
        image_data = base64.b64decode(cropped_image.split(',')[1])

        # PILのImageオブジェクトに変換する
        pil_image = PIL.Image.open(BytesIO(image_data))

        # 一時的なバッファに画像を保存
        buffer = BytesIO()

        # フォーマットをWebPに統一し、画質を下げる
        pil_image.save(buffer, format="WEBP", quality=10, lossless=False)

        # バッファからバイトデータを取得
        buffer.seek(0)
        image_data = buffer.read()

        # UUIDを生成
        filename = str(uuid.uuid4()) + '.webp'
        
        # GCSのバケットにアップロードする
        bucket = gcs.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_data)

        blob.make_public()

        # 透過済みの画像をデータベースに保存する
        new_image = Image(object_name=filename, public_url=blob.public_url, user_id=user_id)
        db.session.add(new_image)
        db.session.commit()

        new_post = Post(title=title, detail=detail, category=category, user_id=user_id, image_id=new_image.id)
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('index'))


@app.route('/detail/<int:id>')
@login_required
def read(id):
    post =Post.query.get(id)
    image = post.image
    restored_image = base64.b64encode(requests.get(image.public_url).content).decode('utf-8')
    return render_template('detail.html', post=post, image=image, restored_image=restored_image)

@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    post = Post.query.get(id)
    image = post.image
    restored_image = base64.b64encode(requests.get(image.public_url).content).decode('utf-8')
    cropped_image = None
    if request.method == 'GET':
        return render_template('update.html', post=post, image=image, restored_image=restored_image, cropped_image=cropped_image)
    else:
        title = request.form.get('title')
        detail = request.form.get('detail')
        category = request.form.get('category')

        # トリミングされた画像データを受け取る
        cropped_image_base64 = request.form.get('crop-result')
        if not cropped_image_base64:
            flash('ファイルがありません')
            return redirect(request.url)
        
        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image_base64 = cropped_image_base64.replace("data:image/jpeg;base64,", "")

        # base64文字列からバイトデータに変換
        cropped_image_data = base64.b64decode(cropped_image_base64)

        # トリミングされた画像データを一時ファイルに保存
        temp_image_file = tempfile.NamedTemporaryFile(delete=False)
        temp_image_file.write(cropped_image_data)
        temp_image_file.close()

        # 一時ファイルのパスをセッションに保存
        session['image_path'] = temp_image_file.name
        session['title'] = title
        session['detail'] = detail
        session['category'] = category

        return render_template('update.html', post=post, image=image, restored_image=restored_image, title=title, detail=detail, category=category, cropped_image=cropped_image_base64)


@app.route('/save_update_rgba/<int:id>', methods=['POST'])
@login_required
def save_update_rgba(id):
    post = Post.query.get(id)
    image = post.image
    if request.method == 'POST':
        #一時ファイルから画像データを読み込む
        with open(session['image_path'], 'rb') as f:
            cropped_image = f.read()
        post.title = session.get('title')
        post.detail = session.get('detail')
        post.category = session.get('category')

        # 画像を透過する
        rgba_image = make_background_transparent(cropped_image)

                # Base64からバイトデータに変換
        rgba_image_data = base64.b64decode(rgba_image)

        # バイトデータからImageオブジェクトに変換
        rgba_image = PIL.Image.open(io.BytesIO(rgba_image_data))

        # 一時的なバッファに画像を保存
        buffer = BytesIO()
        rgba_image.save(buffer, format="WEBP", quality=10, lossless=False)

        # バッファからバイトデータを取得
        buffer.seek(0)
        rgba_image_bytes = buffer.read()

        # GCSのバケットにアップロードする
        bucket = gcs.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(image.object_name)
        blob.upload_from_string(rgba_image_bytes)

        blob.make_public()
        image.public_url = blob.public_url
        db.session.commit()

        # トップページにリダイレクトする
        return redirect(url_for('index'))


@app.route('/save_update_cropped/<int:id>', methods=['POST'])
@login_required
def save_update_cropped(id):
    post = Post.query.get(id)
    image = post.image
    if request.method == 'POST':
        cropped_image = request.form.get('image-src-input')
        post.title = session.get('title')
        post.detail = session.get('detail')
        post.category = session.get('category')

        # データURIスキームを外してデコードする
        image_data = base64.b64decode(cropped_image.split(',')[1])
        
        # PILのImageオブジェクトに変換する
        pil_image = PIL.Image.open(BytesIO(image_data))

        # 一時的なバッファに画像を保存
        buffer = BytesIO()

        # フォーマットをWebPに統一し、画質を下げる
        pil_image.save(buffer, format="WEBP", quality=10, lossless=False)

        # バッファからバイトデータを取得
        buffer.seek(0)
        image_data = buffer.read()

        # GCSのバケットにアップロードする
        bucket = gcs.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(image.object_name)
        blob.upload_from_string(image_data)

        blob.make_public()
        image.public_url = blob.public_url
        db.session.commit()

        return redirect(url_for('index'))


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    post = Post.query.get(id)
    image = post.image

    current_id = current_user.id

    # ログインしているユーザー以外からの削除を防止
    if current_id == post.user_id == image.user_id:

        bucket = gcs.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(image.object_name)
        blob.delete()

        db.session.delete(post)
        db.session.delete(image)
        db.session.commit()

        return redirect('/index')
    else:
        flash('invalid delete')
        return redirect('/index')

@app.route('/outfit', methods=['GET', 'POST'])
@login_required
def outfit():
    if request.method == 'GET':
        user = current_user
        outfit_images = OutfitImage.query.filter_by(user_id=user.id).all()
        # 現在ログインしているユーザー名と画像が持つユーザー名が一致する場合のみ取り出す
        images = Image.query.filter_by(user_id=user.id).all()
        # image.idをキー、エンコードされた画像データをバリューとする辞書を作成
        encoded_images_dict = {image.id: base64.b64encode(requests.get(image.public_url).content).decode('utf-8') for image in images}
        #保存したデータを表示する
        return render_template('outfit.html', outfit_images=outfit_images, encoded_images_dict=encoded_images_dict)
    else:
        user_id = current_user.id
        # 洋服のidの上下セットを登録
        tops_image_id = request.form.get('tops_image')
        bottoms_image_id = request.form.get('bottoms_image')
        if tops_image_id and bottoms_image_id:
            new_outfit_image = OutfitImage(tops_image_id=tops_image_id, bottoms_image_id=bottoms_image_id, user_id=user_id)
            db.session.add(new_outfit_image)
            db.session.commit()
            return redirect('/index')
        else:
            flash('コーデを保存するためにトップスとボトムスの画像をクリックしてください')
            flash('Click on the tops and bottoms images to save the outfit')
            return redirect('/index')

@app.route('/outfit/delete/<int:id>')
@login_required
def delete_outfit(id):
    outfit_image = OutfitImage.query.get(id)

    # ログインしているユーザー以外からの削除を防止
    if current_user.id == outfit_image.user_id:
        db.session.delete(outfit_image)
        db.session.commit()
        return redirect('/outfit')
    else:
        flash('invalid delete')
        return redirect('/outfit')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template('signup.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            # Userのインスタンスを生成
            user = User(username=username, password=generate_password_hash(password, method='sha256'))
            db.session.add(user)
            db.session.commit()
            return redirect('/login')
        except:
            flash('This username is already in use')
            return redirect(request.url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            # Userテーブルからusernameに一致するユーザーを取得
            user = User.query.filter_by(username=username).first()
    
            # usernameに一致するユーザーが存在しない場合
            if user is None:
                flash('User does not exist')
                return redirect(request.url)

            # 提供されたパスワードがハッシュ化されたパスワードと一致するかチェック
            if not check_password_hash(user.password, password):
                flash('Incorrect password')
                return redirect(request.url)
    
            # ユーザーが正常に認証された場合
            login_user(user)
            return redirect('/index')
        except Exception as e:
            # 未知のエラーが発生した場合
            flash('An unexpected error occurred: {}'.format(str(e)))
            return redirect(request.url)


@app.route('/', methods=['GET'])
def top():
    if request.method == 'GET':
        return render_template('top.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)

# 最後消す