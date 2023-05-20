window.onload = function() {
    // croppieインスタンスを初期化する
    const el = document.getElementById('rgba-container');
    const vanilla = new Croppie(el, {
        viewport: { width: 200, height: 250 },
        boundary: { width: 300, height: 300 },
        showZoomer: true,
        enableOrientation: true
    });

    document.getElementById('original-rgba').addEventListener('click', function() {
        // クリックされた画像のsrc属性を取得
        const imgSrc = this.src;

        // 新しい画像のsrcを、クリックした画像のsrcに設定する
        vanilla.bind({
            url: imgSrc,
        });
    });

    document.getElementById('apply-crop').addEventListener('click', function() {
        vanilla.result('base64').then(function(base64) {
            //base64のデータをフォームのinputにセットする
            document.getElementById('crop-result').value = base64;
        });
    });
};