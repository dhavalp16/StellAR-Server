from flask import Blueprint, jsonify, request
from modules.supabase_service import supabase_service


classroom_api = Blueprint('classroom_api', __name__)

@classroom_api.route('/api/classroom/<user_id>', methods=['GET'])
def get_classroom(user_id):
    try:
        classroom_data = supabase_service.query_records("classroom", select="*", filters={"created_by": user_id})
        if not classroom_data:
            return jsonify({'error': 'Classroom not found'}), 404
        return jsonify(classroom_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@classroom_api.route('/api/create_classroom', methods=['POST'])
def create_classroom():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Missing JSON body"}), 400

        response = supabase_service.insert_record(
            "classroom",
            payload
        )

        return jsonify(response.data), 201

    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@classroom_api.route('/api/join_classroom', methods=['POST'])
def join_classroom():
    try:
        payload = request.get_json()
        print(payload)
        if not payload:
            return jsonify({"error": "Missing JSON body"}), 400
        
        classroom_id = supabase_service.query_records("classroom", select="id", filters={"join_code": payload['join_code']})
        if not classroom_id:
            return jsonify({"error": "Classroom not found"}), 404

        insert_record = {
            "classroom_id": classroom_id[0]['id'],
            "user_id": payload['user_id']
        }
        response = supabase_service.insert_record(
            "classroom_members",
            insert_record
        )

        return jsonify(response.data), 200

    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@classroom_api.route('/api/classroom_members/<classroom_id>', methods=['GET'])
def get_classroom_members(classroom_id):
    try:
        classroom_members = supabase_service.query_records("classroom_members", select="*", filters={"classroom_id": classroom_id})
        users = []
        for i in classroom_members:
            user_data = supabase_service.query_records("users", select="*", filters={"id": i['user_id']})
            users.extend(user_data)
        if not classroom_members:
            return jsonify({'error': 'Classroom members not found'}), 404
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
