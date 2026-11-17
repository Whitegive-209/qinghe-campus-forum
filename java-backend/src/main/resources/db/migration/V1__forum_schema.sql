CREATE TABLE forum_user (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 username VARCHAR(30) NOT NULL UNIQUE,
 password VARCHAR(100) NOT NULL,
 nickname VARCHAR(30) NOT NULL DEFAULT '',
 bio VARCHAR(200) NOT NULL DEFAULT '',
 created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;
CREATE TABLE forum_category (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 name VARCHAR(30) NOT NULL UNIQUE,
 slug VARCHAR(40) NOT NULL UNIQUE,
 sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;
CREATE TABLE forum_post (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 author_id BIGINT NOT NULL,
 category_id BIGINT NOT NULL,
 title VARCHAR(100) NOT NULL,
 body TEXT NOT NULL,
 created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (author_id) REFERENCES forum_user(id),
 FOREIGN KEY (category_id) REFERENCES forum_category(id),
 INDEX post_time(created_at DESC,id DESC),
 INDEX category_time(category_id,created_at DESC)
) ENGINE=InnoDB;
CREATE TABLE forum_comment (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 post_id BIGINT NOT NULL,
 author_id BIGINT NOT NULL,
 parent_id BIGINT NULL,
 body VARCHAR(1000) NOT NULL,
 is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY (post_id) REFERENCES forum_post(id) ON DELETE CASCADE,
 FOREIGN KEY (author_id) REFERENCES forum_user(id),
 FOREIGN KEY (parent_id) REFERENCES forum_comment(id),
 INDEX comment_post_time(post_id,created_at,id)
) ENGINE=InnoDB;
CREATE TABLE forum_post_like (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 user_id BIGINT NOT NULL,
 post_id BIGINT NOT NULL,
 FOREIGN KEY (user_id) REFERENCES forum_user(id),
 FOREIGN KEY (post_id) REFERENCES forum_post(id) ON DELETE CASCADE,
 CONSTRAINT unique_user_post_like UNIQUE(user_id,post_id)
) ENGINE=InnoDB;
INSERT INTO forum_category(name,slug,sort_order) VALUES
 ('学习交流','study',1),('校园生活','life',2),('活动广场','events',3),('闲置交易','market',4),('意见建议','suggestions',5);
