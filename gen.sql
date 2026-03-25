create table if not exists digital_paper (
    id integer primary key autoincrement,
    date text not null,
    title text not null,
    author text not null,
    collaborator text not null, -- 通讯员
    photo text not null,
    content text not null,
    page_no text not null,
    page_name text not null default '', -- 版面名
    left_top_x integer not null,
    left_top_y integer not null,
    left_bottom_x integer not null,
    left_bottom_y integer not null,
    right_bottom_x integer not null,
    right_bottom_y integer not null,
    right_top_x integer not null,
    right_top_y integer not null,
    pdf text not null,
    site_id integer null default 1, -- 舟山日报-其他
    is_dump integer not null default 0, -- 是否已上传
    next_page text not null default '', -- 转版下一个版面
    has_previous integer not null default 0 -- 是否接前一版面
);

create table if not exists reporter (
    id integer primary key autoincrement,
    name text not null,
    department text not null
);

create table if not exists duplicate (
    id integer primary key autoincrement,
    digital_paper_id integer not null,
    similary_id integer not null,
    similarity real not null
);