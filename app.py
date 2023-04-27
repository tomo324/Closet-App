from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, send_file
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


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)


@app.route('/index', methods=['GET'])
def index():
    if request.method == 'GET':
        posts = Post.query.all()
        #images = Image.query.all()
        # 画像データをbase64にエンコード
        #restored_images = base64.b64encode(images.data).decode('utf-8')
        return render_template('index.html', posts=posts)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'GET':
        return render_template('create.html')
    else:
        title = request.form.get('title')
        detail = request.form.get('detail')

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

            new_post = Post(title=title, detail=detail)
            db.session.add(new_post)
            db.session.commit()

            new_image = Image(filename=filename, data=data)
            db.session.add(new_image)
            db.session.commit()

            return redirect('/index')

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
    if request.method == 'GET':
        return render_template('update.html', post=post)
    else:
        post.title = request.form.get('title')
        post.detail = request.form.get('detail')

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


if __name__ == "__main__":
    app.run(debug=True)