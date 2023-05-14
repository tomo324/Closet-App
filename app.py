from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from io import BytesIO
import base64

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
    if request.method == 'GET':
        return render_template('create.html')
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
            data = file.read()

            new_post = Post(title=title, detail=detail, category=category)
            db.session.add(new_post)
            db.session.commit()

            new_image = Image(filename=filename, data=data)
            db.session.add(new_image)
            db.session.commit()
            return redirect('/index')
        else:
            flash('ファイルの拡張子がpng, jpg, gifのいずれかであることを確認してください\n  Only png, jpg, and gif are allowed')
            return redirect(request.referrer)

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