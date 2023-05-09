document.addEventListener('DOMContentLoaded', () => {
    const topsImages = document.querySelectorAll('#tops img');
    const bottomsImages = document.querySelectorAll('#bottoms img');
    const topsImageInput = document.getElementById('tops_image');
    const bottomsImageInput = document.getElementById('bottoms_image');
    const topsDisplayArea = document.getElementById('tops_display_area');
    const bottomsDisplayArea = document.getElementById('bottoms_display_area');

    topsImages.forEach((img) => {
        img.addEventListener('click', () => {
            topsImages.forEach((i) => i.classList.remove('selected'));
            img.classList.add('selected');
            topsImageInput.value = img.src;

            //既に画像があれば削除する
            const previousTopsImage = topsDisplayArea.querySelector('.tops');
            if (previousTopsImage) {
                previousTopsImage.remove();
            }

            //画像を追加
            const addTopsImage = document.createElement('img');
            addTopsImage.src = topsImageInput.value;
            addTopsImage.classList.add('tops');
            topsDisplayArea.appendChild(addTopsImage);
        });
    });

    bottomsImages.forEach((img) => {
        img.addEventListener('click', () => {
            bottomsImages.forEach((i) => i.classList.remove('selected'));
            img.classList.add('selected');
            bottomsImageInput.value = img.src;

            //既に画像があれば削除する
            const previousBottomsImage = bottomsDisplayArea.querySelector('.bottoms');
            if (previousBottomsImage) {
                previousBottomsImage.remove();
            }

            //画像を追加
            const addBottomsImage = document.createElement('img');
            addBottomsImage.src = bottomsImageInput.value;
            addBottomsImage.classList.add('bottoms');
            bottomsDisplayArea.appendChild(addBottomsImage);
        });
    });
});
