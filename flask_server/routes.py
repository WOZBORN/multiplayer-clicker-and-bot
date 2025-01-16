from itsdangerous import URLSafeTimedSerializer
from flask import request, jsonify
from flask_restful import Resource
from werkzeug.exceptions import HTTPException

from flask_app import api, app, db
from models import User

# Сериализатор для токенов
serializer = URLSafeTimedSerializer('your_secret_key')


# Обработчик ошибок для возврата JSON вместо HTML
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({'message': e.description}), e.code
    return jsonify({'message': 'Произошла внутренняя ошибка сервера'}), 500


class RegisterUser(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {'message': 'Некорректный запрос, ожидается JSON'}, 400

            telegram_id = data.get('telegram_id')
            tg_nickname = data.get('tg_nickname')
            password = data.get('password')

            if not telegram_id or not tg_nickname or not password:
                return {'message': 'Все поля (telegram_id, tg_nickname, password) обязательны'}, 400

            if User.query.filter((User.telegram_id == telegram_id) | (User.tg_nickname == tg_nickname)).first():
                return {'message': 'Пользователь уже существует'}, 400

            user = User(telegram_id=telegram_id, tg_nickname=tg_nickname)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return {'message': 'Пользователь успешно зарегистрирован'}, 201

        except Exception as e:
            return {'message': 'Ошибка регистрации пользователя', 'error': str(e)}, 500


class LoginUser(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {'message': 'Некорректный запрос, ожидается JSON'}, 400

            tg_nickname = data.get('tg_nickname')
            password = data.get('password')

            if not tg_nickname or not password:
                return {'message': 'Оба поля (tg_nickname, password) обязательны'}, 400

            user = User.query.filter_by(tg_nickname=tg_nickname).first()
            if user and user.check_password(password):
                return {'message': 'Успешный вход'}, 200
            return {'message': 'Неверные учетные данные'}, 401

        except Exception as e:
            return {'message': 'Ошибка авторизации', 'error': str(e)}, 500


class ResetPassword(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {'message': 'Некорректный запрос, ожидается JSON'}, 400

            telegram_id = data.get('telegram_id')
            if not telegram_id:
                return {'message': 'Поле telegram_id обязательно'}, 400

            user = User.query.filter_by(telegram_id=telegram_id).first()
            if user:
                reset_token = serializer.dumps(user.id, salt='password-reset-salt')
                return {'message': 'Токен для сброса пароля создан', 'reset_token': reset_token}, 200
            return {'message': 'Пользователь не найден'}, 404

        except Exception as e:
            return {'message': 'Ошибка генерации токена', 'error': str(e)}, 500


class SetNewPassword(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {'message': 'Некорректный запрос, ожидается JSON'}, 400

            reset_token = data.get('reset_token')
            new_password = data.get('new_password')

            if not reset_token or not new_password:
                return {'message': 'Оба поля (reset_token, new_password) обязательны'}, 400

            try:
                user_id = serializer.loads(reset_token, salt='password-reset-salt', max_age=3600)
            except Exception:
                return {'message': 'Недействительный или истекший токен'}, 400

            user = User.query.get(user_id)
            if user:
                user.set_password(new_password)
                db.session.commit()
                return {'message': 'Пароль успешно изменен'}, 200
            return {'message': 'Пользователь не найден'}, 404

        except Exception as e:
            return {'message': 'Ошибка сброса пароля', 'error': str(e)}, 500


class ShowUserInfo(Resource):
    def get(self, telegram_id):
        try:
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if user:
                return {
                    'telegram_id': user.telegram_id,
                    'tg_nickname': user.tg_nickname,
                    'clicks': user.clicks,
                    'register_date': user.register_date.strftime('%Y-%m-%d %H:%M:%S')
                }, 200
            return {'message': 'Пользователь не найден'}, 404

        except Exception as e:
            return {'message': 'Ошибка получения информации о пользователе', 'error': str(e)}, 500


class SyncClicks(Resource):
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {'message': 'Некорректный запрос, ожидается JSON'}, 400

            tg_nickname = data.get('tg_nickname')
            clicks = data.get('clicks', 0)

            if not tg_nickname:
                return {'message': 'Поле tg_nickname обязательно'}, 400

            user = User.query.filter_by(tg_nickname=tg_nickname).first()
            if user:
                user.clicks += clicks
                db.session.commit()
                return {'message': 'Клики синхронизированы'}, 200
            return {'message': 'Пользователь не найден'}, 404

        except Exception as e:
            return {'message': 'Ошибка синхронизации кликов', 'error': str(e)}, 500


class GetLeaders(Resource):
    def get(self):
        try:
            count = request.args.get('count', 10, type=int)
            leaders = User.query.order_by(User.clicks.desc()).limit(count).all()
            return [{'tg_nickname': user.tg_nickname, 'clicks': user.clicks} for user in leaders], 200

        except Exception as e:
            return {'message': 'Ошибка получения лидеров', 'error': str(e)}, 500


class CheckUser(Resource):
    def get(self, telegram_id):
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if user:
            return {'exists': True}, 200
        return {'exists': False}, 404


api.add_resource(CheckUser, '/check_user/<string:telegram_id>')
api.add_resource(RegisterUser, '/register_user')
api.add_resource(LoginUser, '/login_user')
api.add_resource(ResetPassword, '/reset_password')
api.add_resource(SetNewPassword, '/set_new_password')
api.add_resource(ShowUserInfo, '/show_user_info/<string:telegram_id>')
api.add_resource(SyncClicks, '/sync_clicks')
api.add_resource(GetLeaders, '/get_leaders')
