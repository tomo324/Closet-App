window.onload = function() {
    // 'original-rgba'画像のsrc属性を取得
    let imgSrc = document.getElementById('original-rgba').src;
    
    // 新しいimg要素を作成し、src属性を設定
    let image = document.createElement('img');
    image.id = 'image';
    image.src = imgSrc;
    
    // 'rgba-container'に新しいimg要素を追加
    let el = document.getElementById('rgba-container');
    el.appendChild(image);

    image.onload = function() {
        // 画像が読み込まれたらCropper.jsのインスタンスを初期化
        let cropper = new Cropper(image, {
            aspectRatio: 3 / 4,
            crop(event) {
                console.log(event.detail.x);
                console.log(event.detail.y);
                console.log(event.detail.width);
                console.log(event.detail.height);
                console.log(event.detail.rotate);
                console.log(event.detail.scaleX);
                console.log(event.detail.scaleY);
            },
        });

        document.getElementById('apply-crop').addEventListener('click', function() {
            // 'apply-crop'ボタンがクリックされたらクロップ結果を取得
            let canvas = cropper.getCroppedCanvas();
            // クロップ結果をJPEG形式のbase64エンコードされた文字列として取得
            let base64 = canvas.toDataURL('image/jpeg');
            // base64エンコードされたクロップ結果を'crop-result'フォームのinputにセット
            document.getElementById('crop-result').value = base64;
            console.log("apply-crop was clicked!")
        });
    };
};
