#!/usr/bin/env python3
"""Regenerate Decap schema to match edited JSON; OAuth is intentionally separate."""
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def field(label,name,widget='string',**kwargs):return {'label':label,'name':name,'widget':widget,**kwargs}
def array(label,name,subfields):return field(label,name,'list',fields=subfields)
def simplelist(label,name):return field(label,name,'list',field=field('Пункт','item'))
def file(name,label,path,fields):return {'name':name,'label':label,'file':path,'format':'json','fields':fields}

settings=[
 file('site','Глобальные данные и логотип','content/site.json',[
  field('Бренд','brand'),field('Домен (production)','domain'),field('Email','email'),field('Telegram','telegram'),field('Телефон','phone',required=False),field('ИНН','inn'),field('Год основания','founded'),field('Логотип — оригинальный файл SVG/PNG','logo_image','image',required=False),
  field('Текст о компании','about','text',required=False),field('Подпись на главной','hero_foot',required=False),field('Текст формы','form_description','text',required=False),field('Заголовок формы','form_title',required=False),field('Подтверждённая цена','price_confirmed')]),
 file('redesign','Главная / решения / FAQ','content/redesign.json',[
  field('Основной H1','hero_title'),field('Первый экран: описание','hero_sub','text'),field('Первый экран: факты','hero_note'),field('Текст первой кнопки','primary_cta'),field('Описание бесплатного плана','plan_intro','text'),
  array('Комплекс работ','scope',[field('Название','title'),field('Описание','description','text'),field('Иконка из ZIP (01–39)','icon','number',value_type='int',min=1,max=39)]),
  field('Операционные задачи','operations','list',field=field('Задача','item')),
  array('Вопросы главной','home_faq',[field('Вопрос','q'),field('Ответ','a','text')]),
  array('Три решения','solutions',[field('Слаг','slug'),field('Метка','label'),field('Название','name'),field('Оффер / H1','headline'),field('Введение','intro','text'),field('Цена','price'),field('Кнопка','cta'),field('Иконка (01–39)','icon','number',value_type='int',min=1,max=39),array('Этапы работ','steps',[field('Название этапа','title'),field('Описание этапа','description','text')]),array('FAQ решения','faqs',[field('Вопрос','q'),field('Ответ','a','text')])])]),
 file('cases','Каталог кейсов (9+)', 'content/redesign_cases.json',[
  array('Кейсы','items',[field('URL-слаг','slug'),field('Компания','name'),field('Отрасль','sector'),field('Фильтр отрасли','category','select',options=[{'label':'Производство','value':'manufacturing'},{'label':'Услуги','value':'services'},{'label':'IT','value':'it'}]),field('Крупный показатель','metric'),field('Подпись к показателю','metric_caption'),field('Описание','intro','text'),field('Что сделали','work','list',field=field('Действие','item')),field('Итог','result','text'),field('Период','period'),field('Иконка из ZIP','icon','number',value_type='int',min=1,max=39),field('Статус подтверждения','status','select',options=['needs_approval','approved']),field('Скриншоты и подтверждающие материалы','screenshots','list',field=field('Изображение','image','image'),required=False)])]),
 file('letters','Настоящие благодарственные письма','content/letters.json',[
  array('Письма','items',[field('Клиент','name'),field('Скан письма','image','image',required=False),field('Alt-текст','image_alt',required=False),field('Согласовано к публикации','approved','boolean',default=False)])]),
 file('team','Реальные фотографии команды','content/team.json',[
  array('Участники/роли','items',[field('Роль','role'),field('Реальное имя','name',required=False),field('Должность и задачи','description','text'),field('Метка роли','label'),field('Временная иконка из ZIP','icon','number',value_type='int',min=1,max=39),field('Фото при наличии согласия','photo','image',required=False)])])
]
config={'backend':{'name':'github','repo':'ahatsmmalin-ai/expteam','branch':'main','squash_merges':True},'publish_mode':'editorial_workflow','media_folder':'static/uploads','public_folder':'/assets/uploads','locale':'ru','cms_auth_ready':False,'site_url':'https://expteam-staging.pages.dev','display_url':'https://expteam-staging.pages.dev','collections':[
 {'name':'settings','label':'Настройки / основные данные','files':settings},
 {'name':'articles','label':'Блог / SEO-статьи','folder':'content/posts','create':True,'format':'frontmatter','extension':'md','slug':'{{fields.slug}}','identifier_field':'title','summary':'{{title}} — {{category}} — {{editorial_status}}','preview_path':'blog/{{fields.slug}}/','fields':[
  field('Заголовок H1','title'),field('URL-слаг','slug'),field('Рубрика','category','select',options=[{'label':x[1],'value':x[0]} for x in [('marketing','Маркетинг'),('lidogeneraciya','Лидогенерация'),('reklama','Реклама'),('sajty','Сайты'),('crm','CRM'),('seo','SEO')]]),field('Главный запрос','keyword'),field('SEO description','description','text'),field('Автор','author'),field('Роль автора','author_role',required=False),field('Биография автора','author_bio','text',required=False),field('Обложка','cover_image','image',required=False),field('Alt','image_alt',required=False),field('Статус','editorial_status','select',options=['draft','factcheck','approved'],default='draft'),field('Кто проверил','reviewed_by',required=False),field('Когда проверили','reviewed_on','datetime',required=False,date_format='YYYY-MM-DD',time_format=False,format='YYYY-MM-DD'),field('Источники','source_notes','text',required=False),field('Опубликовано','published','boolean',default=False),field('Дата','date','datetime',date_format='YYYY-MM-DD',time_format=False,format='YYYY-MM-DD'),field('Обновление','modified','datetime',date_format='YYYY-MM-DD',time_format=False,format='YYYY-MM-DD'),field('Связанные услуги (legacy)','related_services','list',field=field('Слаг','slug'),required=False),field('Текст статьи','body','markdown'),field('Отметка редактора','review_note','text',required=False)]},
 {'name':'pages','label':'Новые страницы','folder':'content/pages','create':True,'format':'frontmatter','extension':'md','slug':'{{fields.slug}}','identifier_field':'title','preview_path':'{{fields.section}}/{{fields.slug}}/','fields':[
  field('Название','title'),field('Слаг латиницей','slug'),field('Раздел','section','select',options=['stranicy','materialy','resheniya']),field('SEO Title','seo_title'),field('SEO Description','description','text'),field('H1','h1'),field('Лид','intro','text'),field('Обложка','cover_image','image',required=False),field('Alt обложки','image_alt',required=False),field('Редакционный статус','editorial_status','select',options=['draft','factcheck','approved'],default='draft'),field('Утвердил','reviewed_by',required=False),field('Дата утверждения','reviewed_on',required=False),field('Основания','source_notes','text',required=False),field('Опубликовано','published','boolean',default=False),field('Основной текст','body','markdown')]},
]}
out=ROOT/'static/admin/config.yml';out.write_text('# CMS authorization is NOT enabled. Configure a real OAuth gateway before changing cms_auth_ready.\n'+yaml.safe_dump(config,allow_unicode=True,sort_keys=False,width=125),encoding='utf8')
print('CMS config regenerated, collections:',[x['name'] for x in config['collections']]);print('Settings:',[x['name'] for x in settings])
