window.onload = function() {
    let image = document.createElement('img');
    image.id = 'image';
    document.getElementById('cropped-container').appendChild(image);

    let cropper;

    // ファイルが選択された際のイベント
    document.getElementById('file-input').addEventListener('change', function() {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            image.src = e.target.result;
            // 新しい画像でcropper.jsを初期化する
            cropper = new Cropper(image, {
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
        };
        
        reader.readAsDataURL(this.files[0]);
    });

    document.getElementById('apply-crop').addEventListener('click', function() {
        // ファイルが選択されている場合
        if (cropper) {
            let canvas = cropper.getCroppedCanvas();
            let base64 = canvas.toDataURL('image/jpeg');
            document.getElementById('crop-result').value = base64;
            console.log("apply-crop was clicked!")
        }
    });
};

window.addEventListener('DOMContentLoaded', function() {
    let cropped_image_src = document.getElementById('original-cropped').src;
    document.getElementById('image-src-input').value = cropped_image_src;
});