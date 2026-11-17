# Java版功能测试报告

日期：2026-11-17。Java 17 / Spring Boot 3.5.16 / MySQL 8.0.41。

结果：39项，39项通过，0项失败，0项跳过。

其中28项使用Spring MVC实际处理请求、真实MySQL测试库和事务回滚，另11项验证输入边界及BCrypt哈希。MockMvc覆盖服务器处理链，不等同于完整浏览器端操作或并发性能测试。

原始JUnit XML：`test-results/java_functional_20261117_134757`（本机保留，不上传含运行细节的原始目录）。脚本：`scripts/run_java.py test`，用例源代码在`java-backend/src/test/java/cn/qinghe/forum/`。

| 测试项目（方法名） | 步骤与预期 | 实际结果 | 是否通过 |
| --- | --- | --- | --- |
| `homeAndCategoriesRender` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（1.722秒） | 通过 |
| `loginWrongPassword` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（1.109秒） | 通过 |
| `editingOwnPostWorks` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.579秒） | 通过 |
| `csrfRequired` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.585秒） | 通过 |
| `createPostPersistsOwner` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.556秒） | 通过 |
| `publicationTimeMatchesRealClock` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.535秒） | 通过 |
| `commentDeletionKeepsReplies` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.565秒） | 通过 |
| `pageEscapesUserHtml` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.592秒） | 通过 |
| `loginValidPassword` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.866秒） | 通过 |
| `missingPostIs404` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.605秒） | 通过 |
| `cannotDeleteOthersPost` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.574秒） | 通过 |
| `registrationCreatesHashedPasswordAndLogsIn` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.86秒） | 通过 |
| `likeIsIdempotentAndCanCancel` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.668秒） | 通过 |
| `accountIdentityIsolated` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.575秒） | 通过 |
| `anonymousCannotPost` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.552秒） | 通过 |
| `cannotDeleteOthersComment` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.58秒） | 通过 |
| `replyCannotCrossPosts` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.592秒） | 通过 |
| `logoutClearsAuthentication` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.566秒） | 通过 |
| `profileCanOnlyEditCurrentUser` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.585秒） | 通过 |
| `commentAndReplyPersist` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.571秒） | 通过 |
| `invalidLikeActionRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.585秒） | 通过 |
| `deleteOwnPostCascadesCommentsAndLikes` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.571秒） | 通过 |
| `titleAndBodySearchAndEmptyState` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.591秒） | 通过 |
| `cannotEditOthersPost` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.571秒） | 通过 |
| `detailRendersContent` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.595秒） | 通过 |
| `duplicateRegistrationRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.868秒） | 通过 |
| `categoryAndHotSortingRender` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.606秒） | 通过 |
| `anonymousCannotOpenProtectedForm` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.561秒） | 通过 |
| `profileLengthEnforced` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.015秒） | 通过 |
| `supplementaryCharactersCountedAsOne` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.005秒） | 通过 |
| `emptyPostTextRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.005秒） | 通过 |
| `passwordsMustMatch` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.0秒） | 通过 |
| `unsafeUsernameRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.006秒） | 通过 |
| `shortPasswordRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.005秒） | 通过 |
| `bcryptByteLimitEnforced` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.0秒） | 通过 |
| `bcryptIsSaltedAndVerifiable` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（1.083秒） | 通过 |
| `longBodyRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.006秒） | 通过 |
| `numericPasswordRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.005秒） | 通过 |
| `commonPasswordRejected` | 执行同名JUnit用例；具体请求参数、预期状态、数据库与权限断言见用例源码 | 所有断言完成，无失败或异常（0.007秒） | 通过 |

## 发现并修复的问题

真实页面检查发现发布时间偏移8小时。原因是JDBC按UTC解释数据，但数据库连接会话使用不同的时区。通过Hikari连接初始化语句，仅将本应用会话设为UTC；未修改MySQL全局设置。新增publicationTimeMatchesRealClock回归用例，修复后39项全部重新通过。重启后实际首页时间与13:43创建时刻一致。

## 其他实际验证

- 独立可执行JAR已启动于`http://127.0.0.1:8080`；健康检查返回`backend: java`、`status: ok`。
- 首次5个串行HTTP检查全部通过：首页、健康检查、登录表单CSRF、注册表单、CSS。原始记录见`test-results/java-live-http.json`。
- Edge实际显示Java版中文首页，帖子、分类、搜索框、导航和样式可见；对话中保留可视化观察。未把该首页检查表述为全部浏览器交互测试通过。
- Java独立演示库、性能库、测试库已建立；本轮功能测试只使用test_qinghe_forum_java。旧Django数据库未重置或清空。

## 尚未执行

Java版JMeter并发测试、超过100用户压力测试及JProfiler录制均未测试；Python历史性能数字不作为Java结果。不能根据功能通过声称100用户性能通过。
