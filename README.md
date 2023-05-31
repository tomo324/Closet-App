# クローゼットアプリ

![スクリーンショット (655)](https://github.com/tomo324/Closet-App/assets/102280498/f907dc36-1106-4839-bdf3-43eb811230cd)
![スクリーンショット (657)](https://github.com/tomo324/Closet-App/assets/102280498/3aff1dc8-aeed-4df1-9213-7baaf26e1fd1)


**URL:** [https://tomo324.pythonanywhere.com/](https://tomo324.pythonanywhere.com/)

## 制作物
洋服を管理できるWebアプリ。洋服をトップスとボトムスに分けて保管でき、コーディネートの登録もできる。また、画像はトリミングや背景を透過して保存できる。

### 使用技術
・Python  
・JavaScript  
・Flask  
・MySQL 

### 制作期間  
約1か月　　

## 作った理由
外出先で洋服を購入する際に、既に所持しているものと同じ種類のアイテムを再度購入してしまうことがしばしばあった。全ての洋服を一箇所に整理できるアプリケーションを開発することで、この問題に対策を打つことができると考えた。

## 工夫した点
### GrabCut法の導入
アプリケーションの設計段階から、画像の背景を透過させて洋服だけを表示する機能を付けることを目指していた。しかしながら、既存のAPIを使用すると画像処理に時間がかかり、またコストも高くなるため、代替手段を模索した。その結果、OpenCVのGrabCut法による前景と背景の分離を採用することにした。この方法を採用することで、外部のAPIに頼らずに背景の透過を実現することが可能となり、加えて処理にかかるコストを大幅に抑えることができた。

## 最も苦労した点
### エラーメッセージが表示されない不具合の解決
画像が適切に表示されないという不具合が発生したが、エラーメッセージが出てこなかったため、原因の特定に時間がかかった。デベロッパーツールを使って調査したところ、Data URIスキームが二重に存在することを発見した。具体的には、JavaScriptとPythonの両方でエンコードが行われており、それが重複していたことが明らかになった。この経験から、システム全体を把握し、本質的な部分を確認することの重要性を再認識した。

## 改善点
### 画面表示の遅さ
Google Cloud Storageに画像データを保存しているので、画像取得に時間がかかり、画面遷移の際の待機時間が長くなってしまう。

## 改善案
### キャッシュを利用できるようにする
そのためには、画像をバイナリ形式で取得してData URIスキームにくっつけるのではなく、直接URLから表示するようにする必要がある。
