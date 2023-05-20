from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import base64
import cv2
import numpy as np
import tempfile

# アップロードされる拡張子の制限
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///closet.db'
#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.String(100))
    category = db.Column(db.Enum('tops', 'bottoms'))


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)

class OutfitImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tops_image_id = db.Column(db.Integer, nullable=False)
    bottoms_image_id = db.Column(db.Integer, nullable=False)

def make_background_transparent(image_data):
    #バイト型のデータに変換する
    image_data = image_data.read()
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

    # RGBA画像をBGRAからRGBAに変換する
    rgba_image = cv2.cvtColor(rgba_image, cv2.COLOR_BGRA2RGBA)

    #pngフォーマットにエンコードしてからbase64にエンコードする
    _, encoded_image = cv2.imencode('.png', rgba_image)
    base64_image = base64.b64encode(encoded_image).decode('utf-8')
    return base64_image


@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        tops = Post.query.filter_by(category='tops').all()
        bottoms = Post.query.filter_by(category='bottoms').all()
        images = Image.query.all()
        filename_dict = {image.id: image.filename for image in images}
        # 画像データをbase64にエンコードし、画像idをキーとする辞書に格納
        restored_images_dict = {image.id: base64.b64encode(image.data).decode('utf-8') for image in images}
        return render_template('index.html', tops=tops, bottoms=bottoms, filename_dict=filename_dict, restored_images_dict=restored_images_dict)
    else:
        tops_image_id = request.form.get('tops_image')
        bottoms_image_id = request.form.get('bottoms_image')
        new_outfit_image = OutfitImage(tops_image_id=tops_image_id, bottoms_image_id=bottoms_image_id)
        db.session.add(new_outfit_image)
        db.session.commit()
        return redirect('/index')

@app.route('/create', methods=['GET', 'POST'])
def create():
    rgba_image = None
    if request.method == 'GET':
        return render_template('create.html', rgba_image=rgba_image)
    else:
        title = request.form.get('title')
        detail = request.form.get('detail')
        category = request.form.get('category')

        # ファイルがなかった場合の処理
        if 'file' not in request.files:
            flash('ファイルがありません')
            return redirect(request.url)
        # データの取り出し
        file = request.files['file']
        # ファイル名がなかった時の処理
        if file.filename == '':
            flash('ファイルがありません')
            return redirect(request.url)
            # ファイルのチェック
        if file and allowed_file(file.filename):
            # 危険な文字を削除（サニタイズ処理）
            filename = secure_filename(file.filename)
            # ファイルの保存
            file = request.files['file']

            #ファイルの拡張子に基づいてmime_typeを決める
            ext = file.filename.rsplit('.', 1)[1].lower()
            mime_type = 'png' if ext == 'png' else 'jpeg' if ext in ['jpg', 'jpeg'] else 'gif'

            # 画像を透過する
            rgba_image = make_background_transparent(file)

            #透過済みの画像を一時フォルダに保存する
            decoded_rgba = base64.b64decode(rgba_image)
            temp_image_file = tempfile.NamedTemporaryFile(delete=False)
            temp_image_file.write(decoded_rgba)
            temp_image_file.close()

            # 一時ファイルのパスをセッションに保存する
            session['image_path'] = temp_image_file.name
            session['filename'] = filename
            session['title'] = title
            session['detail'] = detail
            session['category'] = category

            return render_template('create.html', title=title, detail=detail, category=category, rgba_image=rgba_image, filename=filename, mime_type=mime_type)
        else:
            flash('ファイルの拡張子がpng, jpg, gifのいずれかであることを確認してください\n  Only png, jpg, and gif are allowed')
            return redirect(request.referrer)

@app.route('/save', methods=['GET', 'POST'])
def save():
    if request.method == 'GET':
        #一時ファイルから画像データを読み込む
        with open(session['image_path'], 'rb') as f:
            rgba_image = f.read()
        filename = session.get('filename')
        title = session.get('title')
        detail = session.get('detail')
        category = session.get('category')

        # 透過済みの画像をデータベースに保存する
        new_post = Post(title=title, detail=detail, category=category)
        db.session.add(new_post)
        db.session.commit()

        new_image = Image(filename=filename, data=rgba_image)
        db.session.add(new_image)
        db.session.commit()

        # ホームページにリダイレクトする
        return redirect(url_for('index'))
    else:
        rgba_image = request.form.get('crop-result')
        # 'data:image/jpeg;base64,'の部分を取り除く
        rgba_image = rgba_image.replace("data:image/jpeg;base64,", "")
        #透過済みの画像を一時フォルダに保存する
        decoded_rgba = base64.b64decode(rgba_image)
        temp_image_file = tempfile.NamedTemporaryFile(delete=False)
        temp_image_file.write(decoded_rgba)
        temp_image_file.close()

        # 一時ファイルのパスをセッションに保存する
        session['image_path'] = temp_image_file.name
        return redirect(url_for('save'))


@app.route('/detail/<int:id>')
def read(id):
    post =Post.query.get(id)
    image = Image.query.get(id)
    # 画像データをbase64にエンコード
    restored_image = base64.b64encode(image.data).decode('utf-8')
    return render_template('detail.html', post=post, image=image, restored_image=restored_image)

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    post = Post.query.get(id)
    image = Image.query.get(id)
    restored_image = base64.b64encode(image.data).decode('utf-8')
    if request.method == 'GET':
        return render_template('update.html', post=post, image=image, restored_image=restored_image)
    else:
        post.title = request.form.get('title')
        post.detail = request.form.get('detail')
        post.category = request.form.get('category')

        # ファイルがなかった場合の処理
        if 'file' not in request.files:
            flash('ファイルがありません')
            return redirect(request.url)
        # データの取り出し
        file = request.files['file']
        # ファイル名がなかった時の処理
        if file.filename == '':
            flash('ファイルがありません')
            return redirect(request.url)
        # ファイルのチェック
        if file and allowed_file(file.filename):
            # 危険な文字を削除（サニタイズ処理）
            filename = secure_filename(file.filename)
            # ファイルの保存
            image.filename = filename
            image.data = file.read()
            db.session.commit()
            return redirect('/index')
        else:
            flash('ファイルの拡張子がpng, jpg, gifのいずれかであることを確認してください\n  Only png, jpg, and gif are allowed')
            return redirect(request.referrer)

@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get(id)
    image = Image.query.get(id)

    db.session.delete(post)
    db.session.commit()

    db.session.delete(image)
    db.session.commit()
    return redirect('/index')

def allowed_file(filename):
    # .があるかどうかのチェックと拡張子の確認
    # OKなら1、だめなら0
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/outfit', methods=['GET'])
def outfit():
    if request.method == 'GET':
        outfit_images = OutfitImage.query.all()
        images = Image.query.all()
        # 画像データをbase64にエンコードし、画像idをキーとする辞書に格納
        restored_images_dict = {image.id: base64.b64encode(image.data).decode('utf-8') for image in images}
        #保存したデータを表示する
        return render_template('outfit.html', outfit_images=outfit_images, restored_images_dict=restored_images_dict)

@app.route('/outfit/delete/<int:id>')
def delete_outfit(id):
    outfit_image = OutfitImage.query.get(id)
    db.session.delete(outfit_image)
    db.session.commit()
    return redirect('/outfit')

if __name__ == "__main__":
    app.run(debug=True)