from functools import lru_cache
import glob
from PIL import Image
import base64
import requests

# bg 360 * 140 = 50400
# patch 50 * 50 = 2500


def download(index):
    '''下载验证码样本图片'''
    url = 'https://iv.jd.com/slide/g.html'
    response = requests.get(url)
    img_json = response.json()
    y = img_json['y']
    bg_base64 = img_json['bg']
    bg_bytes = base64.b64decode(bg_base64)
    file_name = 'sample/{}_bg_{}.png'.format(index, y)
    with open(file_name, 'wb') as f:
        f.write(bg_bytes)


def is_same_category_img(img1, img2):
    '''
    判断两张图片是否属于同一类别
    '''
    width, height = img1.size
    img1_pixels = img1.load()
    img2_pixels = img2.load()
    same_pixel_count = sum(is_pixel_equal(img1_pixels, img2_pixels, x, y) for x in range(width) for y in range(height))
    return same_pixel_count > 45000
    # return same_pixel_count


def combine_img(file2imgs):
    '''
    去掉缺口 合并图片
    '''
    file, img = next(iter(file2imgs.items()))
    new_img = Image.new(img.mode, img.size)
    pim = new_img.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            color = get_color(file2imgs, x, y)
            if not color:  # 样本不足
                return None
            else:
                pim[x, y] = color
    return new_img


def get_color(file2imgs, x, y, patch_size=50):
    '''
    从一堆图片中挑选出坐标(x,y) 不在缺口范围的像素点
    '''
    for file in file2imgs:
        patch_y = int(file.replace('.png', '').split('_')[-1])
        if y > patch_y + patch_size or y < patch_y:
            return file2imgs[file].load()[x, y]


def is_pixel_equal(pixels1, pixels2, x, y, threshold=30):
    """
    判断两个像素是否相同
    :param pixels1: 图片1的所有像素点
    :param pixels2: 图片2的所有像素点
    :param x: 位置x
    :param y: 位置y
    :param threshold: 阈值
    :return: 像素是否相同
    """
    pixel1 = pixels1[x, y]
    pixel2 = pixels2[x, y]
    return all((abs(pixel1[0] - pixel2[0]) < threshold, abs(pixel1[1] - pixel2[1]) < threshold, abs(pixel1[2] - pixel2[2]) < threshold))


def get_gap_x_percent(img_file_name):
    '''
    获取缺口位置 X 轴偏移量的百分比
    '''
    diff_list = []
    img = Image.open(img_file_name)
    target = get_target_img(img)
    target_pixels = target.load()
    img_pixels = img.load()
    for x in range(target.size[0]):
        diff_count = sum(not is_pixel_equal(target_pixels, img_pixels, x, y) for y in range(target.size[1]))
        diff_list.append(diff_count)
    for index in range(len(diff_list) - 10):
        if diff_list[index] > 10:
            if all(diff_list[index + i] > 10 for i in range(1, 6)):  # 连续5列存在不同
                return index / img.size[0]


def get_target_img(img):
    '''
    根据有缺口的图片 去获取 没有缺口的图片
    '''
    imgs = get_imgs()
    for i in imgs:
        if is_same_category_img(img, i):
            return i


@lru_cache()
def get_imgs():
    '''
    获取所有的标准图片
    '''
    return [Image.open(file) for file in glob.glob('normal/*.png')]


def group_imgs(file2imgs):
    '''
    将样本图片进行分组
    '''
    files = list(file2imgs)
    groups = []
    while files:
        current = files[0]
        current_group = {current: file2imgs[current]}
        for other in files[1:]:
            if is_same_category_img(file2imgs[current], file2imgs[other]):
                current_group[other] = file2imgs[other]
        for file in current_group:
            files.remove(file)
        groups.append(current_group)
    return groups


if __name__ == '__main__':
    # 1.下载样本图片
    for index in range(250):
        print('正在下载 {}张图片...'.format(index))
        download(index)

    # 2.将下载好的样本图片分类 获取每一类的原图片
    files = glob.glob('sample/*_bg_*.png')
    file2imgs = {file: Image.open(file) for file in files}
    print('正在对图片进行分组...')
    groups = group_imgs(file2imgs)
    print('一共 {} 张图片，分成 {} 组'.format(len(files), len(groups)))
    for index, group in enumerate(groups):
        print('正在处理第 {} 组'.format(index))
        new_img = combine_img(group)
        if new_img:
            new_img.save('normal/{}.png'.format(index))
        else:
            print('第 {} 组样本不足'.format(index))
