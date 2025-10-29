# nutridata数据爬取

- 官网地址：https://nutridata.cn/home
- 爬取需要注册登录账号才能看到隐藏数据
- 数据内容包括食物成分库和菜肴库的图片和基础数据

## 1、使用selenium进行数据爬取

通过对应的网页格式找到规律后使用selenium库进行自动化爬取。

### 1.dish_data菜肴库数据

**爬取代码**：selenium_get_nutrition_data、selenium_get_nutrition_category

**爬取的数据**：dish_data、dish_images

- 爬取菜品名称、成分、计量单位、图片地址（动态的，一段时间会失效）、本地图片路径、菜肴做法、能量及宏量营养素、维生素、矿物质、单位量。
- 主要爬取"名称"、"能量"、"分类"、等作为数据对应和关联辅助。
- 菜肴库图片。

### 2、food_data食物成分库

**爬取代码**：selenium_get_nutrition_ingredient_data、selenium_get_nutrition_ingredient_category

**爬取的数据**：food_data、food_images

- 爬取食物成分名称、成分、计量单位、图片地址（动态的，一段时间会失效）、本地图片路径、能量及宏量营养素、维生素、矿物质、单位量。
- 主要爬取"一级分类"、"二级分类"、"名称"、等数据作为数据对应和关联辅助。
- 食物成分库图片。

## 2、数据说明

通过出入数据库将数据格式化为excel,为后续的分类清洗做准备

dish_images存放菜品图片，food_images存放食物图片

my_h_dish_category.xlsx主要存菜品分类数据，my_h_dish_info_all.xlsx存储所有菜肴数据，共25668条数据

my_h_food_nutrition.xlsx主要存食物成分分类数据，my_h_dish_info_all.xlsx存储食物成分数据，共4004条数据

**对应数据格式说明：**

my_h_dish_info_all：

| 食品 ID              | id               |
| :------------------- | ---------------- |
| 作为爬取的数据行标识 | dish_id          |
| 菜肴名称             | dish_name        |
| 成分及含量           | composition      |
| 菜肴总质量           | measurement_unit |
| 菜品对应图片地址     | img_url          |
| 菜肴对应路径         | img_path         |
| 能量及宏量营养素     | macronutrients   |
| 所有维生素含量       | vitamin          |
| 矿物质含量           | minerals         |
| 菜肴的计量单位       | quantity         |
| 菜肴的做法           | cooking_method   |

my_h_dish_info_all：

| 食品 ID          | food_id                   |
| ---------------- | ------------------------- |
| 食品名称         | food_name                 |
| 配料             | ingredients               |
| 计量单位         | unit_of_measurement       |
| 图片 URL         | image_url                 |
| 本地图片路径     | local_image_path          |
| 单位数量         | unit_amount               |
| 能量和宏量营养素 | energy_and_macronutrients |
| 维生素           | vitamins                  |
| 矿物质           | minerals                  |

## 3、数据处理

### dish_cleaning处理菜肴库

数据格式及翻译：

| id                            |                            |
| ----------------------------- | -------------------------- |
| dish_id                       | 菜品id                     |
| dish_name                     | 菜品名称                   |
| composition                   | 菜品成分                   |
| measurement_unit              | 菜品单位                   |
| quantity                      | 菜品计量单位               |
| cooking_method                | 菜品做法                   |
| category                      | 菜品分类                   |
| energy_nrv_val                | 能量NRV值                  |
| energy_nrv_unit               | 能量NRV单位                |
| energy_content_val            | 能量含量值                 |
| energy_content_unit           | 能量含量单位               |
| protein_nrv_val               | 蛋白质NRV值                |
| protein_nrv_unit              | 蛋白质NRV单位              |
| protein_content_val           | 蛋白质含量值               |
| protein_content_unit          | 蛋白质含量单位             |
| fat_nrv_val                   | 脂肪NRV值                  |
| fat_nrv_unit                  | 脂肪NRV单位                |
| fat_content_val               | 脂肪含量值                 |
| fat_content_unit              | 脂肪含量单位               |
| carbohydrates_nrv_val         | 碳水化合物NRV值            |
| carbohydrates_nrv_unit        | 碳水化合物NRV单位          |
| carbohydrates_content_val     | 碳水化合物含量值           |
| carbohydrates_content_unit    | 碳水化合物含量单位         |
| vitamin_A_nrv_val             | 维生素ANRV值               |
| vitamin_A_nrv_unit            | 维生素ANRV单位             |
| vitamin_A_content_val         | 维生素A含量值              |
| vitamin_A_content_unit        | 维生素A含量单位            |
| vitamin_E_nrv_val             | 维生素ENRV值               |
| vitamin_E_nrv_unit            | 维生素ENRV单位             |
| vitamin_E_content_val         | 维生素E含量值              |
| vitamin_E_content_unit        | 维生素E含量单位            |
| thiamine_nrv_val              | 硫胺素（维生素B1）NRV值    |
| thiamine_nrv_unit             | 硫胺素（维生素B1）NRV单位  |
| thiamine_content_val          | 硫胺素（维生素B1）含量值   |
| thiamine_content_unit         | 硫胺素（维生素B1）含量单位 |
| riboflavin_nrv_val            | 核黄素（维生素B2）NRV值    |
| riboflavin_nrv_unit           | 核黄素（维生素B2）NRV单位  |
| riboflavin_content_val        | 核黄素（维生素B2）含量值   |
| riboflavin_content_unit       | 核黄素（维生素B2）含量单位 |
| vitamin_B₆_nrv_val            | 维生素B₆NRV值              |
| vitamin_B₆_nrv_unit           | 维生素B₆NRV单位            |
| vitamin_B₆_content_val        | 维生素B₆含量值             |
| vitamin_B₆_content_unit       | 维生素B₆含量单位           |
| vitamin_B₁₂_nrv_val           | 维生素B₁₂NRV值             |
| vitamin_B₁₂_nrv_unit          | 维生素B₁₂NRV单位           |
| vitamin_B₁₂_content_val       | 维生素B₁₂含量值            |
| vitamin_B₁₂_content_unit      | 维生素B₁₂含量单位          |
| niacin_nrv_val                | 烟酸（维生素B3）NRV值      |
| niacin_nrv_unit               | 烟酸（维生素B3）NRV单位    |
| niacin_content_val            | 烟酸（维生素B3）含量值     |
| niacin_content_unit           | 烟酸（维生素B3）含量单位   |
| folic_acid_nrv_val            | 叶酸NRV值                  |
| folic_acid_nrv_unit           | 叶酸NRV单位                |
| folic_acid_content_val        | 叶酸含量值                 |
| folic_acid_content_unit       | 叶酸含量单位               |
| vitamin_C_nrv_val             | 维生素CNRV值               |
| vitamin_C_nrv_unit            | 维生素CNRV单位             |
| vitamin_C_content_val         | 维生素C含量值              |
| vitamin_C_content_unit        | 维生素C含量单位            |
| biotin_nrv_val                | 生物素（维生素B7）NRV值    |
| biotin_nrv_unit               | 生物素（维生素B7）NRV单位  |
| biotin_content_val            | 生物素（维生素B7）含量值   |
| biotin_content_unit           | 生物素（维生素B7）含量单位 |
| total_choline_nrv_val         | 总胆碱NRV值                |
| total_choline_nrv_unit        | 总胆碱NRV单位              |
| total_choline_content_val     | 总胆碱含量值               |
| total_choline_content_unit    | 总胆碱含量单位             |
| vitamin_D_nrv_val             | 维生素DNRV值               |
| vitamin_D_nrv_unit            | 维生素DNRV单位             |
| vitamin_D_content_val         | 维生素D含量值              |
| vitamin_D_content_unit        | 维生素D含量单位            |
| vitamin_K_nrv_val             | 维生素KNRV值               |
| vitamin_K_nrv_unit            | 维生素KNRV单位             |
| vitamin_K_content_val         | 维生素K含量值              |
| vitamin_K_content_unit        | 维生素K含量单位            |
| pantothenic_acid_nrv_val      | 泛酸（维生素B5）NRV值      |
| pantothenic_acid_nrv_unit     | 泛酸（维生素B5）NRV单位    |
| pantothenic_acid_content_val  | 泛酸（维生素B5）含量值     |
| pantothenic_acid_content_unit | 泛酸（维生素B5）含量单位   |
| sodium_nrv_val                | 钠NRV值                    |
| sodium_nrv_unit               | 钠NRV单位                  |
| sodium_content_val            | 钠含量值                   |
| sodium_content_unit           | 钠含量单位                 |
| potassium_nrv_val             | 钾NRV值                    |
| potassium_nrv_unit            | 钾NRV单位                  |
| potassium_content_val         | 钾含量值                   |
| potassium_content_unit        | 钾含量单位                 |
| magnesium_nrv_val             | 镁NRV值                    |
| magnesium_nrv_unit            | 镁NRV单位                  |
| magnesium_content_val         | 镁含量值                   |
| magnesium_content_unit        | 镁含量单位                 |
| iron_nrv_val                  | 铁NRV值                    |
| iron_nrv_unit                 | 铁NRV单位                  |
| iron_content_val              | 铁含量值                   |
| iron_content_unit             | 铁含量单位                 |
| zinc_nrv_val                  | 锌NRV值                    |
| zinc_nrv_unit                 | 锌NRV单位                  |
| zinc_content_val              | 锌含量值                   |
| zinc_content_unit             | 锌含量单位                 |
| calcium_nrv_val               | 钙NRV值                    |
| calcium_nrv_unit              | 钙NRV单位                  |
| calcium_content_val           | 钙含量值                   |
| calcium_content_unit          | 钙含量单位                 |
| phosphorus_nrv_val            | 磷NRV值                    |
| phosphorus_nrv_unit           | 磷NRV单位                  |
| phosphorus_content_val        | 磷含量值                   |
| phosphorus_content_unit       | 磷含量单位                 |
| selenium_nrv_val              | 硒NRV值                    |
| selenium_nrv_unit             | 硒NRV单位                  |
| selenium_content_val          | 硒含量值                   |
| selenium_content_unit         | 硒含量单位                 |
| iodine_nrv_val                | 碘NRV值                    |
| iodine_nrv_unit               | 碘NRV单位                  |
| iodine_content_val            | 碘含量值                   |
| iodine_content_unit           | 碘含量单位                 |
| copper_nrv_val                | 铜NRV值                    |
| copper_nrv_unit               | 铜NRV单位                  |
| copper_content_val            | 铜含量值                   |
| copper_content_unit           | 铜含量单位                 |
| manganese_nrv_val             | 锰NRV值                    |
| manganese_nrv_unit            | 锰NRV单位                  |
| manganese_content_val         | 锰含量值                   |
| manganese_content_unit        | 锰含量单位                 |

### food_cleaning处理食品成分库

-  my_h_food_info_alldata.xlsx为处理之后的excel

数据格式及翻译：

| food_id                      | 食品ID                                       |
| ---------------------------- | -------------------------------------------- |
| first_category               | 一级分类                                     |
| second_category              | 二级分类                                     |
| food_name                    | 食品名称                                     |
| ingredients                  | 配料                                         |
| unit_of_measurement          | 计量单位                                     |
| unit_amount                  | 单位数量                                     |
| energy_nrv_percent           | 能量营养素参考值百分比（NRV%）               |
| energy_nrv_unit              | 能量营养素参考值单位                         |
| energy_num                   | 能量数值                                     |
| energy_unit                  | 能量单位                                     |
| protein_nrv_percent          | 蛋白质营养素参考值百分比（NRV%）             |
| protein_nrv_unit             | 蛋白质营养素参考值单位                       |
| protein_num                  | 蛋白质数值                                   |
| protein_unit                 | 蛋白质单位                                   |
| fat_nrv_percent              | 脂肪营养素参考值百分比（NRV%）               |
| fat_nrv_unit                 | 脂肪营养素参考值单位                         |
| fat_num                      | 脂肪数值                                     |
| fat_unit                     | 脂肪单位                                     |
| carbohydrates_nrv_percent    | 碳水化合物营养素参考值百分比（NRV%）         |
| carbohydrates_nrv_unit       | 碳水化合物营养素参考值单位                   |
| carbohydrates_num            | 碳水化合物数值                               |
| carbohydrates_unit           | 碳水化合物单位                               |
| vitamin_A_nrv_percent        | 维生素A营养素参考值百分比（NRV%）            |
| vitamin_A_nrv_unit           | 维生素A营养素参考值单位                      |
| vitamin_A_num                | 维生素A数值                                  |
| vitamin_A_unit               | 维生素A单位                                  |
| vitamin_E_nrv_percent        | 维生素E营养素参考值百分比（NRV%）            |
| vitamin_E_nrv_unit           | 维生素E营养素参考值单位                      |
| vitamin_E_num                | 维生素E数值                                  |
| vitamin_E_unit               | 维生素E单位                                  |
| thiamine_nrv_percent         | 硫胺素（维生素B1）营养素参考值百分比（NRV%） |
| thiamine_nrv_unit            | 硫胺素（维生素B1）营养素参考值单位           |
| thiamine_num                 | 硫胺素（维生素B1）数值                       |
| thiamine_unit                | 硫胺素（维生素B1）单位                       |
| riboflavin_nrv_percent       | 核黄素（维生素B2）营养素参考值百分比（NRV%） |
| riboflavin_nrv_unit          | 核黄素（维生素B2）营养素参考值单位           |
| riboflavin_num               | 核黄素（维生素B2）数值                       |
| riboflavin_unit              | 核黄素（维生素B2）单位                       |
| niacin_nrv_percent           | 烟酸（维生素B3）营养素参考值百分比（NRV%）   |
| niacin_nrv_unit              | 烟酸（维生素B3）营养素参考值单位             |
| niacin_num                   | 烟酸（维生素B3）数值                         |
| niacin_unit                  | 烟酸（维生素B3）单位                         |
| folic_acid_nrv_percent       | 叶酸营养素参考值百分比（NRV%）               |
| folic_acid_nrv_unit          | 叶酸营养素参考值单位                         |
| folic_acid_num               | 叶酸数值                                     |
| folic_acid_unit              | 叶酸单位                                     |
| biotin_nrv_percent           | 生物素（维生素B7）营养素参考值百分比（NRV%） |
| biotin_nrv_unit              | 生物素（维生素B7）营养素参考值单位           |
| biotin_num                   | 生物素（维生素B7）数值                       |
| biotin_unit                  | 生物素（维生素B7）单位                       |
| total_choline_nrv_percent    | 总胆碱营养素参考值百分比（NRV%）             |
| total_choline_nrv_unit       | 总胆碱营养素参考值单位                       |
| total_choline_num            | 总胆碱数值                                   |
| total_choline_unit           | 总胆碱单位                                   |
| sodium_nrv_percent           | 钠营养素参考值百分比（NRV%）                 |
| sodium_nrv_unit              | 钠营养素参考值单位                           |
| sodium_num                   | 钠数值                                       |
| sodium_unit                  | 钠单位                                       |
| potassium_nrv_percent        | 钾营养素参考值百分比（NRV%）                 |
| potassium_nrv_unit           | 钾营养素参考值单位                           |
| potassium_num                | 钾数值                                       |
| potassium_unit               | 钾单位                                       |
| magnesium_nrv_percent        | 镁营养素参考值百分比（NRV%）                 |
| magnesium_nrv_unit           | 镁营养素参考值单位                           |
| magnesium_num                | 镁数值                                       |
| magnesium_unit               | 镁单位                                       |
| iron_nrv_percent             | 铁营养素参考值百分比（NRV%）                 |
| iron_nrv_unit                | 铁营养素参考值单位                           |
| iron_num                     | 铁数值                                       |
| iron_unit                    | 铁单位                                       |
| zinc_nrv_percent             | 锌营养素参考值百分比（NRV%）                 |
| zinc_nrv_unit                | 锌营养素参考值单位                           |
| zinc_num                     | 锌数值                                       |
| zinc_unit                    | 锌单位                                       |
| calcium_nrv_percent          | 钙营养素参考值百分比（NRV%）                 |
| calcium_nrv_unit             | 钙营养素参考值单位                           |
| calcium_num                  | 钙数值                                       |
| calcium_unit                 | 钙单位                                       |
| phosphorus_nrv_percent       | 磷营养素参考值百分比（NRV%）                 |
| phosphorus_nrv_unit          | 磷营养素参考值单位                           |
| phosphorus_num               | 磷数值                                       |
| phosphorus_unit              | 磷单位                                       |
| selenium_nrv_percent         | 硒营养素参考值百分比（NRV%）                 |
| selenium_nrv_unit            | 硒营养素参考值单位                           |
| selenium_num                 | 硒数值                                       |
| selenium_unit                | 硒单位                                       |
| iodine_nrv_percent           | 碘营养素参考值百分比（NRV%）                 |
| iodine_nrv_unit              | 碘营养素参考值单位                           |
| iodine_num                   | 碘数值                                       |
| iodine_unit                  | 碘单位                                       |
| copper_nrv_percent           | 铜营养素参考值百分比（NRV%）                 |
| copper_nrv_unit              | 铜营养素参考值单位                           |
| copper_num                   | 铜数值                                       |
| copper_unit                  | 铜单位                                       |
| manganese_nrv_percent        | 锰营养素参考值百分比（NRV%）                 |
| manganese_nrv_unit           | 锰营养素参考值单位                           |
| manganese_num                | 锰数值                                       |
| manganese_unit               | 锰单位                                       |
| vitamin_B₆_nrv_percent       | 维生素B₆营养素参考值百分比（NRV%）           |
| vitamin_B₆_nrv_unit          | 维生素B₆营养素参考值单位                     |
| vitamin_B₆_num               | 维生素B₆数值                                 |
| vitamin_B₆_unit              | 维生素B₆单位                                 |
| vitamin_D_nrv_percent        | 维生素D营养素参考值百分比（NRV%）            |
| vitamin_D_nrv_unit           | 维生素D营养素参考值单位                      |
| vitamin_D_num                | 维生素D数值                                  |
| vitamin_D_unit               | 维生素D单位                                  |
| vitamin_B₁₂_nrv_percent      | 维生素B₁₂营养素参考值百分比（NRV%）          |
| vitamin_B₁₂_nrv_unit         | 维生素B₁₂营养素参考值单位                    |
| vitamin_B₁₂_num              | 维生素B₁₂数值                                |
| vitamin_B₁₂_unit             | 维生素B₁₂单位                                |
| vitamin_C_nrv_percent        | 维生素C营养素参考值百分比（NRV%）            |
| vitamin_C_nrv_unit           | 维生素C营养素参考值单位                      |
| vitamin_C_num                | 维生素C数值                                  |
| vitamin_C_unit               | 维生素C单位                                  |
| vitamin_K_nrv_percent        | 维生素K营养素参考值百分比（NRV%）            |
| vitamin_K_nrv_unit           | 维生素K营养素参考值单位                      |
| vitamin_K_num                | 维生素K数值                                  |
| vitamin_K_unit               | 维生素K单位                                  |
| pantothenic_acid_nrv_percent | 泛酸（维生素B5）营养素参考值百分比（NRV%）   |
| pantothenic_acid_nrv_unit    | 泛酸（维生素B5）营养素参考值单位             |
| pantothenic_acid_num         | 泛酸（维生素B5）数值                         |
| pantothenic_acid_unit        | 泛酸（维生素B5）单位                         |

# 数据来源说明

- 数据仅供学习参考，不做商业用途。