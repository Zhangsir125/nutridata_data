# nutridata上的菜肴库数据

## 1、菜肴库数据说明

- **dish_data文件夹**：my_h_dish_category.xlsx主要存菜品分类数据，my_h_dish_info_all.xlsx存储所有菜肴数据，共25668条数据

  > **对应数据格式说明：**
  >
  > id:作为数据排序
  >
  > dish_id:作为爬取的数据行标识
  >
  > dish_name:菜肴名称
  >
  > composition:成分及含量
  >
  > measurement_unit:菜肴总质量
  >
  > img_url:菜品对应图片地址
  >
  > img_path：菜肴对应路径
  >
  > macronutrients:能量及宏量营养素
  >
  > vitamin:所有维生素含量
  >
  > minerals:矿物质含量
  >
  > quantity:菜肴的计量单位
  >
  > cooking_method:菜肴的做法

- **dish_images文件夹**：存储所爬取的图片文件夹，共10732张图片

## 2、数据分析

- 有效数据共24611条，由于是按照网页链接对应的8456到34123依次爬取，其中1057条为网页中的空数据。
- img_url和img_path中有效数据共有10732，未获取到的图片在网站中显示无图片
- 能量、蛋白质、脂肪、碳水化合物存为一个字段，方便爬取
- 维生素和矿物质同理
- quantity和cooking_method也有无数据部分，均为对应页面中无数据，共3874条数据