#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :  app.py
@Time    :  2023/12/13
@Author  :  HDUZN
@Version :  1.1
@Contact :  hduzn@vip.qq.com
@License :  (C)Copyright 2023-2024
@Desc    :  1.提交关键词：获取每一课的关键词提交链接
            2.显示词云：显示每个年级每一课的词云结果
            
            pip install flask flask_sqlalchemy gevent pandas openpyxl wordcloud
'''

from wordcloud import WordCloud
from flask import Flask, render_template, request, jsonify
from gevent.pywsgi import WSGIServer
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, and_
import os, base64, json
from io import BytesIO
from collections import Counter

app = Flask(__name__)
app.secret_key = 'wordcloudsyssss'

current_dir = os.getcwd()
db_file = os.path.join(current_dir, 'static', 'db', 'sz_wordcloud.db')
# 配置数据库地址
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
# 跟踪数据库的修改-->不建议开启未来的版本中会移除
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

grade_info = {
    '3-1': '三年级上册',
    '3-2': '三年级下册',
    '4-1': '四年级上册',
    '4-2': '四年级下册',
    '5-1': '五年级上册',
    '5-2': '五年级下册',
    '6-1': '六年级上册',
    '6-2': '六年级下册',
}
grade_info_reverse = {v: k for k, v in grade_info.items()}

class Data(db.Model) :
    __tablename__ = "data"
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.String(3))
    lesson = db.Column(db.Integer)
    class_n = db.Column(db.String(3))
    stu_id = db.Column(db.Integer)
    name = db.Column(db.String(256))
    words = db.Column(db.String(256))

    def __repr__(self) :
        return '<User: %s %s %s %s %s %s %s>' % (self.id,self.grade,self.lesson,self.class_n,self.stu_id,self.name,self.words)

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 提交关键词
@app.route('/submit_all', methods=['GET', 'POST'])
def submit_all():
    global grade_info, grade_info_reverse
    grade_info_options = list(grade_info.values()) # 所有的年级
    lessons = [i for i in range(1, 16)]
    lesson_options = ['第{}课'.format(row) for row in lessons] # 所有的课程

    submit_url = ''
    get_grade = ''
    get_lesson = ''
    if request.method == 'POST':
        get_grade = request.form.get('grade')
        get_lesson = request.form.get('lesson')
        # print(grade_info, lesson_info) # 五年级上册 第10课

        # 查询
        if get_grade and get_lesson:
            grade = grade_info_reverse[get_grade] # '5-1'
            # lesson = int(get_lesson[1:3]) # 10
            lesson = int(get_lesson.replace('第', '').replace('课', '')) # 9
            server = request.host # 127.0.0.1:5005
            submit_url = f"http://{server}/submit/{grade}/{lesson}"

    return render_template('submit_all.html', grade_options=grade_info_options, lesson_options=lesson_options, submit_url=submit_url, selected_grade=get_grade, selected_lesson=get_lesson)

@app.route('/submit/<grade>/<int:lesson>', methods=['GET', 'POST'])
def submit(grade, lesson):
    message = ''
    if request.method == 'POST':
        class_n = request.form.get('class_n')
        stu_id = request.form.get('stu_id')
        name = request.form.get('name')
        keyword1 = request.form.get('keyword1')
        keyword2 = request.form.get('keyword2')
        keyword3 = request.form.get('keyword3')
        grade = request.form.get('grade')
        lesson = request.form.get('lesson')
        # print(class_n, stu_id, name, keyword1, keyword2, keyword3, grade, lesson)
    
        keywords = [keyword1]
        if keyword2:
            keywords.append(keyword2)
        if keyword3:
            keywords.append(keyword3)
        words = ','.join(keywords)
        # print(words)

        # 写入数据库
        existing_data = Data.query.filter_by(grade=grade,lesson=lesson,class_n=class_n,name=name).first()
        if existing_data:
            message='已提交，无法重复提交'
        else:
            data = Data(grade=grade, lesson=lesson, class_n=class_n, stu_id=stu_id, name=name, words=words)
            db.session.add(data)
            db.session.commit()

            return render_template('success.html')  # 提交成功后显示的页面
        
    return render_template('submit.html', grade=grade, lesson=lesson, message=message)

# 查询结果
@app.route('/query_all', methods=['GET', 'POST'])
def query_all():
    global grade_info, grade_info_reverse
    # 获取唯一的年级
    results = db.session.query(distinct(Data.grade)).all()
    grade_options = [row[0] for row in results] # 所有的年级
    grade_info_options = [grade_info[option] for option in grade_options]
    # print('grade_info_options:', grade_info_options)

    # 获取唯一的课程
    results = db.session.query(distinct(Data.lesson)).all()
    # lesson_options = [row[0] for row in results] # 所有的课程
    lesson_options = ['第{}课'.format(row[0]) for row in results] # 所有的课程
    # print('lesson_options:', lesson_options)

    # 获取唯一的班级
    results = db.session.query(distinct(Data.class_n)).all()
    class_n_options = [row[0] for row in results]

    wordcloud_base64 = None
    top5_words = []
    get_grade = ''
    get_lesson = ''
    get_class_n = ''
    if request.method == 'POST':
        get_grade = request.form.get('grade')
        get_lesson = request.form.get('lesson')
        get_class_n = request.form.get('class_n')
        # print(get_grade, get_lesson, get_class_n) # 五年级上册 第10课 501

        # 查询
        if get_grade and get_lesson:
            grade = grade_info_reverse[get_grade] # '5-1'
            # lesson = int(get_lesson[1:3]) # 10
            lesson = int(get_lesson.replace('第', '').replace('课', '')) # 9
            if get_class_n:
                results = Data.query.with_entities(Data.words).filter(and_(Data.grade==grade,Data.lesson==lesson,Data.class_n==get_class_n)).all()
            else:
                results = Data.query.with_entities(Data.words).filter(and_(Data.grade==grade,Data.lesson==lesson)).all()
            # query_results = cursor.fetchall()
            # print('query_results:', results)

            if results:
                word_list = []
                for result in results:
                    words = result[0].split(',')
                    word_list.extend(words)
                # print('word_list:', word_list)

                # 生成词云
                wordcloud_base64 = generate_word_cloud(word_list)
                # 统计 word_list 中每个元素出现的次数
                word_count = Counter(word_list)
                # 获取出现次数最多的 5 个元素
                top5_words = word_count.most_common(5)
            else:
                wordcloud_base64 = None
                top5_words = []
            
            results = Data.query.with_entities(Data.class_n).filter_by(grade=grade, lesson=lesson).distinct().all()
            class_n_options = [option[0] for option in results]

    return render_template('query_all.html', grade_options=grade_info_options, lesson_options=lesson_options, class_n_options=class_n_options, wordcloud=wordcloud_base64, top5_words=top5_words, selected_grade=get_grade, selected_lesson=get_lesson, selected_class_n=get_class_n)

@app.route('/get_class_options', methods=['GET'])
def get_class_options():
    global grade_info_reverse
    get_grade = request.args.get('grade')
    get_lesson = request.args.get('lesson')
    grade = grade_info_reverse[get_grade] # '5-1'
    lesson = int(get_lesson.replace('第', '').replace('课', '')) # 9

    # 查询数据库，获取相应的班级选项
    query_results = db.session.query(distinct(Data.class_n)).filter(Data.grade==grade, Data.lesson==lesson).all()
    class_options = [result[0] for result in query_results]
    # print('class_options:', class_options)
    class_options_json = json.dumps(class_options)
    # print('class_options_json:', class_options_json)

    # 将班级选项转换为 JSON 格式并返回
    return jsonify(class_options_json)

# 生成词云
def generate_word_cloud(word_list):
    # 创建词云
    font_p = os.path.join(current_dir, 'static', 'fonts', 'SimHei.ttf')
    wc = WordCloud(font_path=font_p, background_color='white', width=600, height=400)
    wordcloud = wc.generate(' '.join(word_list))

    # 将词云图片转换为 base64 编码的字符串
    wordcloud_img = wordcloud.to_image()
    img_bytes = BytesIO()
    wordcloud_img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    wordcloud_base64 = base64.b64encode(img_bytes).decode()
    
    return wordcloud_base64

# 写入数据库
def insert_test_data():
    new_data = Data(grade='4-1',lesson=10,class_n='401',stu_id=1,name='张三',words='Python,C++,Java')
    db.session.add(new_data)
    new_data2 = Data(grade='4-1',lesson=10,class_n='401',stu_id=2,name='李四',words='Python,C#,PHP')
    db.session.add(new_data2)
    new_data3 = Data(grade='4-1',lesson=10,class_n='401',stu_id=3,name='王五',words='Python,C#,C语言')
    db.session.add(new_data3)
    db.session.commit()

# db init
def db_init():
    with app.app_context():
        # 删除表
        db.drop_all()
        # 创建表
        db.create_all()

        #insert_test_data()       

if __name__ == '__main__':
    # db init
    db_init()

    http_server = WSGIServer(('0.0.0.0', 5005), app)
    http_server.serve_forever()
