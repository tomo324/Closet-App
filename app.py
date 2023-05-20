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
    data = db.Column(db.LargeBinary)

class OutfitImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tops_image_id = db.Column(db.Integer, nullable=False)
    bottoms_image_id = db.Column(db.Integer, nullable=False)

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
        # 画像データをbase64にエンコードし、画像idをキーとする辞書に格納
        restored_images_dict = {image.id: base64.b64encode(image.data).decode('utf-8') for image in images}
        return render_template('index.html', tops=tops, bottoms=bottoms, restored_images_dict=restored_images_dict)
    else:
        tops_image_id = request.form.get('tops_image')
        bottoms_image_id = request.form.get('bottoms_image')
        new_outfit_image = OutfitImage(tops_image_id=tops_image_id, bottoms_image_id=bottoms_image_id)
        db.session.add(new_outfit_image)
        db.session.commit()
        return redirect('/index')

@app.route('/create', methods=['GET', 'POST'])
def create():
    cropped_image = None
    if request.method == 'GET':
        return render_template('create.html', cropped_image=cropped_image)
    else:
        title = request.form.get('title')
        detail = request.form.get('detail')
        category = request.form.get('category')

        # クロップされた画像データを受け取る
        cropped_image_base64 = request.form.get('crop-result') 
        if not cropped_image_base64:
            flash('ファイルがありません')
            return redirect(request.url)
        
        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image_base64 = cropped_image_base64.replace("data:image/jpeg;base64,", "")

        # base64文字列からバイトデータに変換
        cropped_image_data = base64.b64decode(cropped_image_base64)

        # クロップされた画像データを一時ファイルに保存
        temp_image_file = tempfile.NamedTemporaryFile(delete=False)
        temp_image_file.write(cropped_image_data)
        temp_image_file.close()

        # 一時ファイルのパスをセッションに保存
        session['image_path'] = temp_image_file.name
        session['title'] = title
        session['detail'] = detail
        session['category'] = category

        return render_template('create.html', title=title, detail=detail, category=category, cropped_image=cropped_image_base64)


@app.route('/save', methods=['GET', 'POST'])
def save():
    if request.method == 'GET':
        #一時ファイルから画像データを読み込む
        with open(session['image_path'], 'rb') as f:
            cropped_image = f.read()
        title = session.get('title')
        detail = session.get('detail')
        category = session.get('category')

        # 画像を透過する
        rgba_image = make_background_transparent(cropped_image)
        rgba_image_bytes = base64.b64decode(rgba_image)

        new_post = Post(title=title, detail=detail, category=category)
        db.session.add(new_post)
        db.session.commit()

        # 透過済みの画像をデータベースに保存する
        new_image = Image(data=rgba_image_bytes)
        db.session.add(new_image)
        db.session.commit()

        # ホームページにリダイレクトする
        return redirect(url_for('index'))
    else:
        cropped_image = request.form.get('image-src-input')
        title = session.get('title')
        detail = session.get('detail')
        category = session.get('category')

        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image = cropped_image.replace("data:image/jpeg;base64,", "")
        # トリミング済みの画像をデコードする
        decoded_cropped = base64.b64decode(cropped_image)

        new_post = Post(title=title, detail=detail, category=category)
        db.session.add(new_post)
        db.session.commit()

        # トリミング済みの画像をデータベースに保存する
        new_image = Image(data=decoded_cropped)
        db.session.add(new_image)
        db.session.commit()

        return redirect(url_for('index'))


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
    cropped_image = None
    if request.method == 'GET':
        return render_template('update.html', post=post, image=image, restored_image=restored_image, cropped_image=cropped_image)
    else:
        title = request.form.get('title')
        detail = request.form.get('detail')
        category = request.form.get('category')

        # クロップされた画像データを受け取る
        cropped_image_base64 = request.form.get('crop-result') 
        if not cropped_image_base64:
            flash('ファイルがありません')
            return redirect(request.url)
        
        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image_base64 = cropped_image_base64.replace("data:image/jpeg;base64,", "")

        # base64文字列からバイトデータに変換
        cropped_image_data = base64.b64decode(cropped_image_base64)

        # クロップされた画像データを一時ファイルに保存
        temp_image_file = tempfile.NamedTemporaryFile(delete=False)
        temp_image_file.write(cropped_image_data)
        temp_image_file.close()

        # 一時ファイルのパスをセッションに保存
        session['image_path'] = temp_image_file.name
        session['title'] = title
        session['detail'] = detail
        session['category'] = category

        return render_template('update.html', post=post, image=image, restored_image=restored_image, title=title, detail=detail, category=category, cropped_image=cropped_image_base64)
    
@app.route('/save_update/<int:id>', methods=['GET', 'POST'])
def save_update(id):
    post = Post.query.get(id)
    image = Image.query.get(id)
    if request.method == 'GET':
        #一時ファイルから画像データを読み込む
        with open(session['image_path'], 'rb') as f:
            cropped_image = f.read()
        post.title = session.get('title')
        post.detail = session.get('detail')
        post.category = session.get('category')

        # 画像を透過する
        rgba_image = make_background_transparent(cropped_image)
        rgba_image_bytes = base64.b64decode(rgba_image)

        image.data = rgba_image_bytes
        db.session.commit()

        # トップページにリダイレクトする
        return redirect(url_for('index'))
    else:
        cropped_image = request.form.get('image-src-input')
        post.title = session.get('title')
        post.detail = session.get('detail')
        post.category = session.get('category')

        # 'data:image/jpeg;base64,'の部分を取り除く
        cropped_image = cropped_image.replace("data:image/jpeg;base64,", "")
        # トリミング済みの画像をデコードする
        decoded_cropped = base64.b64decode(cropped_image)

        image.data = decoded_cropped
        db.session.commit()
        return redirect(url_for('index'))


@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get(id)
    image = Image.query.get(id)

    db.session.delete(post)
    db.session.commit()

    db.session.delete(image)
    db.session.commit()
    return redirect('/index')

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