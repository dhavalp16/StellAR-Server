from flask import Blueprint, jsonify, request
from modules.supabase_service import supabase_service


classroom_api = Blueprint('classroom_api', __name__)

@classroom_api.route('/api/classroom/<classroom_id>', methods=['GET'])
def get_classroom(classroom_id):
    try:
        classroom_data = supabase_service.query_records("classroom", select="*", filters={"id": classroom_id})
        
        if not classroom_data:
            return jsonify({'error': 'Classroom not found'}), 200
        
        classroom_author = supabase_service.query_records("users", select="user_name", filters={"id": classroom_data[0]['created_by']})
        classroom_details = {
            "classroom": classroom_data[0]['name'],
            "author": classroom_author[0]['user_name'],
            "count_member": len(classroom_data)
        }
        
        return jsonify(classroom_details), 200
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


@classroom_api.route('/api/classroomjoined/<user_id>', methods=['GET'])
def get_classroom_joined(user_id):
    try:
        # 1. Fetch all memberships for this user
        classroom_joined = supabase_service.query_records("classroom_members", select="*", filters={"user_id": user_id})
        print(classroom_joined)
        # 2. Check immediately if list is empty
        if not classroom_joined:
            return jsonify(classroom_joined), 200
        
        # Initialize as a list to return a JSON array
        classrooms = []
        
        for i in classroom_joined:
            # 3. Fetch details safely
            classroom_res = supabase_service.query_records("classroom", select="name", filters={"id": i['classroom_id']})
            
            # Note: Fetching user details using i['user_id'] gets the member's name.
            user_res = supabase_service.query_records("users", select="user_name", filters={"id": i['user_id']})

            # Fetch members to count them.
            members_res = supabase_service.query_records("classroom_members", select="id", filters={"classroom_id": i['classroom_id']})
            member_count = len(members_res) if members_res else 0

            # 4. Check if records exist before accessing [0]
            if classroom_res and user_res:
                # Construct a dictionary directly (JSON serializable)
                # DO NOT use a custom class instance here.
                joined_classroom = {
                    "classroom_id": i['classroom_id'],
                    "name": classroom_res[0]['name'],
                    "author": user_res[0]['user_name'],
                    "count_member": member_count
                }
                classrooms.append(joined_classroom)
            else:
                # Log or handle inconsistent data
                print(f"Data inconsistency found for member record: {i}")
                continue
            
        return jsonify(classrooms), 200

    except Exception as e:
        print(f"Error in get_classroom_joined: {e}") # Print error to console for debugging
        return jsonify({'error': str(e)}), 500

@classroom_api.route('/api/classroommodels/<classroom_id>', methods=['GET'])
def get_classroom_models(classroom_id):
    try:
        classroom_models = supabase_service.query_records("models", select="*", filters={"uploader_id": classroom_id})
        if not classroom_models:
            return jsonify({'error': 'Classroom models not found'}), 404
        return jsonify(classroom_models), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
